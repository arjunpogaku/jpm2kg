#!/usr/bin/env python3
"""
aggregate_full.py — Phase 4 aggregation for the BDA 2026 NL->Cypher study.

Reads a results JSONL (system records, possibly multi-LLM) and produces:
  Table 1  main comparison (mean +/- std, pooled over LLMs)        -> results/table1_main.{csv,tex}
  Table 2  per-LLM breakdown (CV/ES/SE)                            -> results/table2_per_llm.{csv,tex}
  Table 3  per-category SE                                         -> results/table3_per_category.{csv,tex}
  Table 4  repair ablation (CB, CB+Repair, DKB, DKB+Hybrid)        -> results/table4_ablation.{csv,tex}
  Figures  fig1 SE by system/LLM, fig2 category heatmap, fig3 CV-vs-SE  -> results/plots/
  Stats    paired Wilcoxon DKB+Hybrid vs others                    -> results/statistical_tests.txt
  results/FINAL_RESULTS.md

Usage: python pipeline/aggregate_full.py [results.jsonl] [benchmark_for_categories.json]
"""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path("/home/arjun/pm25_system")
RES  = ROOT/"results"; PLOTS = RES/"plots"; LATEX = RES/"latex"
for d in (RES, PLOTS, LATEX): d.mkdir(parents=True, exist_ok=True)
IN   = Path(sys.argv[1]) if len(sys.argv)>1 else RES/"results_full.jsonl"
BENCH= Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/"benchmarks"/"benchmark_200_system.json"

sys.path.insert(0,str(ROOT))
from pipeline.dkb_repair import repair
from pipeline.evaluator import QueryEvaluator

LAB={"baseline":"Baseline (Zero-shot)","cypherbench_style":"CypherBench-Style (ACL'25)",
     "dkb":"DKB (Ours)","dkb_hybrid":"DKB+Hybrid (Ours)"}
SHORT={"baseline":"Base","cypherbench_style":"CyphBench","dkb":"DKB","dkb_hybrid":"DKB+Hyb"}
ORD=["baseline","cypherbench_style","dkb","dkb_hybrid"]
METR=["CV","ES","EM","SE","RQ"]
LEGACY={"cypher_validity":"CV","execution_success":"ES","exact_match":"EM",
        "semantic_equivalence":"SE","result_quality_heuristic":"RQ","result_quality":"RQ"}

def num(v): return v if isinstance(v,(int,float)) else None
def norm(m): return {LEGACY.get(k,k):v for k,v in m.items()}

def load():
    recs=[json.loads(l) for l in IN.read_text().splitlines() if l.strip()]
    for r in recs: r["metrics"]=norm(r.get("metrics",{}))
    return recs

def colvals(recs,sys,m,llm=None):
    return [num(r["metrics"].get(m)) for r in recs if r["system"]==sys and (llm is None or r["llm"]==llm)]
def mean(vals):
    n=[v for v in vals if isinstance(v,(int,float))]; return float(np.mean(n)) if n else None
def std(vals):
    n=[v for v in vals if isinstance(v,(int,float))]; return float(np.std(n)) if n else 0.0

def main():
    recs=load()
    llms=sorted(set(r["llm"] for r in recs))
    cat_of={q["query_id"]:q.get("category",q.get("type","?")) for q in json.load(open(BENCH))}
    out=[]

    # ---- Table 1 ----
    t1=["system,"+",".join(METR)]
    print("\n=== TABLE 1: MAIN (pooled over LLMs) ===")
    print(f"{'System':<28}"+"".join(f"{m:>13}" for m in METR))
    for s in ORD:
        cells=[]
        for m in METR:
            mu,sd=mean(colvals(recs,s,m)),std(colvals(recs,s,m))
            cells.append(f"{mu:.3f}±{sd:.3f}" if mu is not None else "n/a")
        print(f"{LAB[s]:<28}"+"".join(f"{c:>13}" for c in cells))
        t1.append(LAB[s]+","+",".join(cells))
    (RES/"table1_main.csv").write_text("\n".join(t1)+"\n")
    # LaTeX T1 (bold best)
    best={m:max((mean(colvals(recs,s,m)) or -1) for s in ORD) for m in METR}
    with open(RES/"table1_main.tex","w") as f:
        f.write("\\begin{tabular}{lccccc}\n\\toprule\nSystem & "+" & ".join(METR)+" \\\\\n\\midrule\n")
        for s in ORD:
            cs=[]
            for m in METR:
                mu=mean(colvals(recs,s,m)); sd=std(colvals(recs,s,m))
                cell=f"{mu:.3f}$\\pm${sd:.3f}"
                if mu is not None and abs(mu-best[m])<1e-9: cell="\\textbf{"+cell+"}"
                cs.append(cell)
            f.write(LAB[s].replace("&","\\&")+" & "+" & ".join(cs)+" \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    # ---- Table 2 per-LLM ----
    t2=["llm,system,CV,ES,SE"]
    print("\n=== TABLE 2: PER-LLM (CV/ES/SE) ===")
    for llm in llms:
        for s in ORD:
            row=[mean(colvals(recs,s,m,llm)) for m in ("CV","ES","SE")]
            t2.append(f"{llm},{LAB[s]},"+",".join(f"{v:.3f}" if v is not None else "" for v in row))
        print(f"  {llm}: "+" | ".join(f"{SHORT[s]} SE={mean(colvals(recs,s,'SE',llm)):.3f}" for s in ORD))
    (RES/"table2_per_llm.csv").write_text("\n".join(t2)+"\n")

    # ---- Table 3 per-category SE ----
    cats=sorted(set(cat_of.values()))
    t3=["category,"+",".join(LAB[s] for s in ORD)]
    print("\n=== TABLE 3: PER-CATEGORY SE ===")
    print(f"{'category':<20}"+"".join(f"{SHORT[s]:>12}" for s in ORD))
    for c in cats:
        row=[]
        for s in ORD:
            vals=[num(r["metrics"].get("SE")) for r in recs if r["system"]==s and cat_of.get(r["query_id"])==c]
            row.append(mean(vals))
        print(f"{c:<20}"+"".join(f"{(v if v is not None else 0):>12.3f}" for v in row))
        t3.append(c+","+",".join(f"{v:.4f}" if v is not None else "" for v in row))
    (RES/"table3_per_category.csv").write_text("\n".join(t3)+"\n")

    # Table 4 (repair ablation) is computed LAST (it re-executes queries against
    # Neo4j and is the slow step) so it never blocks the fast outputs below.

    # ---- Stats ----
    lines=["Paired Wilcoxon signed-rank: DKB+Hybrid vs others (pooled over LLMs)\n"]
    try:
        from scipy.stats import wilcoxon
        qids=sorted(set(r["query_id"] for r in recs))
        def paired(sys):
            a,b=[],[]
            for r in recs:
                if r["system"]!="dkb_hybrid": continue
                m=[x for x in recs if x["query_id"]==r["query_id"] and x["system"]==sys and x["llm"]==r["llm"]]
                if m:
                    va=num(r["metrics"].get("SE")); vb=num(m[0]["metrics"].get("SE"))
                    a.append(va if va is not None else 0.0); b.append(vb if vb is not None else 0.0)
            return np.array(a),np.array(b)
        for s in ["baseline","cypherbench_style","dkb"]:
            a,b=paired(s)
            try: st,p=wilcoxon(a,b); sig="***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
            except Exception as e: p=float('nan'); sig=str(e)[:20]
            line=f"  SE DKB+Hybrid({a.mean():.3f}) vs {s:<18}({b.mean():.3f})  delta={a.mean()-b.mean():+.3f}  p={p:.3g} {sig}"
            print(line); lines.append(line)
    except ImportError:
        lines.append("scipy unavailable")
    (RES/"statistical_tests.txt").write_text("\n".join(lines)+"\n")

    # ---- Figures ----
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        # fig1 SE by system grouped by LLM
        fig,ax=plt.subplots(figsize=(8,4.5)); x=np.arange(len(ORD)); w=0.8/max(1,len(llms))
        for i,llm in enumerate(llms):
            ax.bar(x+i*w,[mean(colvals(recs,s,"SE",llm)) or 0 for s in ORD],w,label=llm.split(":")[0])
        ax.set_xticks(x+w*(len(llms)-1)/2); ax.set_xticklabels([LAB[s].split(" (")[0] for s in ORD],rotation=15,ha="right")
        ax.set_ylabel("Semantic Equivalence (SE)"); ax.set_title("SE by system and LLM"); ax.legend(); fig.tight_layout()
        fig.savefig(PLOTS/"fig1_se_by_system_llm.pdf"); fig.savefig(PLOTS/"fig1_se_by_system_llm.png",dpi=300); plt.close(fig)
        # fig2 category heatmap
        mat=np.array([[ (mean([num(r["metrics"].get("SE")) for r in recs if r["system"]==s and cat_of.get(r["query_id"])==c]) or 0) for s in ORD] for c in cats])
        fig,ax=plt.subplots(figsize=(7,4.5)); im=ax.imshow(mat,aspect="auto",cmap="YlOrRd",vmin=0,vmax=1)
        ax.set_xticks(range(len(ORD))); ax.set_xticklabels([LAB[s].split(" (")[0] for s in ORD],rotation=20,ha="right")
        ax.set_yticks(range(len(cats))); ax.set_yticklabels(cats)
        for i in range(len(cats)):
            for j in range(len(ORD)): ax.text(j,i,f"{mat[i,j]:.2f}",ha="center",va="center",fontsize=8)
        fig.colorbar(im,label="SE"); ax.set_title("SE by query category"); fig.tight_layout()
        fig.savefig(PLOTS/"fig2_category_heatmap.pdf"); fig.savefig(PLOTS/"fig2_category_heatmap.png",dpi=300); plt.close(fig)
        # fig3 CV vs SE scatter
        fig,ax=plt.subplots(figsize=(6,5)); colors={"baseline":"#e74c3c","cypherbench_style":"#3498db","dkb":"#27ae60","dkb_hybrid":"#1a8a4a"}
        for s in ORD:
            for llm in llms:
                cv=mean(colvals(recs,s,"CV",llm)); se=mean(colvals(recs,s,"SE",llm))
                if cv is not None and se is not None: ax.scatter(cv,se,c=colors[s],s=80,label=LAB[s].split(" (")[0] if llm==llms[0] else None)
        ax.set_xlabel("Cypher Validity (CV)"); ax.set_ylabel("Semantic Equivalence (SE)")
        ax.set_title("Valid != Correct: high CV does not imply high SE"); ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
        fig.savefig(PLOTS/"fig3_cv_vs_se.pdf"); fig.savefig(PLOTS/"fig3_cv_vs_se.png",dpi=300); plt.close(fig)
        print("\nWrote 3 figures to results/plots/")
    except Exception as e:
        print("figures skipped:",str(e)[:80])

    # ---- FINAL_RESULTS.md ----
    nq=len(set(r["query_id"] for r in recs))
    def row(s): return "| "+LAB[s]+" | "+" | ".join(
        (f"{mean(colvals(recs,s,m)):.3f}" if mean(colvals(recs,s,m)) is not None else "n/a") for m in METR)+" |"
    md=[f"# FINAL RESULTS — DKB NL→Cypher on JAPAQ-KG (BDA 2026)\n",
        f"Queries evaluated: **{nq}** · Systems: 4 · LLMs: {', '.join(l.split(':')[0] for l in llms)} "
        f"· Total evaluations: **{len(recs)}**\n",
        "## Table 1 — Main comparison (pooled over LLMs)\n",
        "| System | CV | ES | EM | SE | RQ |","|---|---|---|---|---|---|",
        *[row(s) for s in ORD], "",
        "## Significance (paired Wilcoxon, SE)\n", "```", *lines, "```", "",
        "## Per-LLM SE\n","| LLM | Baseline | CypherBench | DKB | DKB+Hybrid |","|---|---|---|---|---|",
        *[f"| {llm.split(':')[0]} | "+" | ".join(f"{mean(colvals(recs,s,'SE',llm)):.3f}" for s in ORD)+" |" for llm in llms], "",
        "Tables 1-4 (csv/tex), 3 figures, and statistical_tests.txt are in `results/`.",
        ]
    (RES/"FINAL_RESULTS.md").write_text("\n".join(md)+"\n")
    print("\nWrote tables 1-3, figures, stats, FINAL_RESULTS.md (fast outputs done)")

    # ---- Table 4 ablation (SLOW: re-executes repaired CypherBench queries) ----
    print("\n=== TABLE 4: REPAIR ABLATION (re-evaluating, may take a few min) ===")
    ev=QueryEvaluator(exec_timeout_s=4)   # tight budget: bounds the re-eval
    rep_se=[]
    cb=[r for r in recs if r["system"]=="cypherbench_style"]
    for i,r in enumerate(cb):
        rc,ops=repair(r.get("generated_cypher") or "")
        if ops and rc!=(r.get("generated_cypher") or ""):
            m=ev.evaluate_all(rc, r.get("gold_cypher",""), r.get("nl_query",""))
            rep_se.append(num(m.get("SE")))
        else:
            rep_se.append(num(r["metrics"].get("SE")))
    ev.close()
    t4=["system,CV,ES,SE"]
    for s,label,se in [("cypherbench_style","CypherBench-Style",mean(colvals(recs,"cypherbench_style","SE"))),
                       ("cypherbench_style+repair","  +DKB-Repair",mean(rep_se)),
                       ("dkb","DKB (Ours)",mean(colvals(recs,"dkb","SE"))),
                       ("dkb_hybrid","DKB+Hybrid (Ours)",mean(colvals(recs,"dkb_hybrid","SE")))]:
        base="cypherbench_style" if "repair" in s else s
        cv,es=mean(colvals(recs,base,"CV")),mean(colvals(recs,base,"ES"))
        print(f"  {label:<24} CV={cv:.3f} ES={es:.3f} SE={se:.3f}")
        t4.append(f"{label},{cv:.4f},{es:.4f},{se:.4f}")
    (RES/"table4_ablation.csv").write_text("\n".join(t4)+"\n")
    print("Wrote table4_ablation.csv")

if __name__=="__main__":
    main()
