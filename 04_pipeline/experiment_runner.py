"""
experiment_runner.py — ExperimentRunner for Japan PM2.5 NL-to-Cypher evaluation.

Reported design:
  6 prompting systems × 4 LLMs × 150 queries = 3,600 evaluations
  fine-tuned baseline × 1 model × 150 queries =  150 evaluations
  Total:                                        3,750 evaluations

Features:
  - Append-only JSONL results (never overwrites)
  - Checkpoint/flush every 50 queries
  - Resume: skip already-completed (query_id, system, llm) combinations
  - tqdm progress bar with system|llm|query_id|ETA
  - Print running average VM-F1 (stored as SE) every 100 queries
  - 30s timeout per query, 2 retries, graceful skip on failure
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):   # type: ignore
        return it

# Make this directory importable whichever way the runner is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    # Self-contained public package layout.
    from systems import QueryGenerationSystems
    from evaluator import QueryEvaluator
except ImportError:  # historical layout
    from pipeline.systems import QueryGenerationSystems
    from pipeline.evaluator import QueryEvaluator

# ── Paths ──────────────────────────────────────────────────────────────────────

_PKG = Path(__file__).resolve().parent.parent

BENCHMARK_PATH  = Path(os.environ.get(
    "BENCHMARK_PATH", _PKG / "02_benchmark" / "aircypher150_benchmark.json"))
DEFAULT_RESULTS = Path(os.environ.get(
    "RESULTS_FILE", _PKG / "05_results" / "raw" / "results_rerun.jsonl"))
CHECKPOINT_DIR  = Path(os.environ.get(
    "CHECKPOINT_DIR", _PKG / "05_results" / "checkpoints"))
CHECKPOINT_N    = 50    # flush checkpoint every N completed evaluations

# The four models reported in the paper.
DEFAULT_LLMS = [
    "llama3.2:3b",
    "gemma2:9b",
    "qwen2.5-coder:32b",
    "qwen2.5:72b",
]

# The six prompting configurations, run against each LLM.
LLM_SYSTEMS = [
    "baseline",            # Baseline
    "cypherbench_style",   # Schema
    "schema_plus_values",  # Schema+Values
    "dkb_no_examples",     # DKB-NoExamples
    "dkb",                 # DKB
    "dkb_hybrid",          # DKB+Hybrid
]
# Systems with a fixed single model (System 3)
FIXED_SYSTEMS = ["text2cypher_finetuned"]   # no LLM arg; model is internal

QUERY_TIMEOUT_S = 30
QUERY_RETRIES   = 2
PRINT_SE_EVERY  = 100   # print running avg VM-F1 (field `SE`) every N evaluations


class ExperimentRunner:
    """
    Orchestrates the full competitive evaluation pipeline.
    Call run() to start (or resume) evaluation.
    """

    def __init__(
        self,
        results_file: str = str(DEFAULT_RESULTS),
        benchmark_path: str = str(BENCHMARK_PATH),
        exec_timeout_s: float = QUERY_TIMEOUT_S,
    ):
        self.results_file = Path(results_file)
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

        self.benchmark_path = Path(benchmark_path)
        self.queries   = self._load_queries()
        self._done     = self._load_done_set()
        self._systems  = QueryGenerationSystems()
        self._evaluator = QueryEvaluator(exec_timeout_s=exec_timeout_s)

    # ── Setup helpers ──────────────────────────────────────────────────────────

    def _load_queries(self) -> List[Dict]:
        data = json.loads(self.benchmark_path.read_text())
        if isinstance(data, list):
            return data
        # Handle dict-keyed format
        return list(data.values())

    def _load_done_set(self) -> set:
        """Return set of (query_id, system, llm) for already-completed evals."""
        done = set()
        if self.results_file.exists():
            for line in self.results_file.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        done.add((r["query_id"], r["system"], r.get("llm", "")))
                    except (json.JSONDecodeError, KeyError):
                        pass
        return done

    def _append(self, record: Dict) -> None:
        with open(self.results_file, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _save_checkpoint(self, n_total_done: int) -> None:
        status = {
            "timestamp":        datetime.now().isoformat(),
            "evaluations_done": n_total_done,
            "results_file":     str(self.results_file),
        }
        (CHECKPOINT_DIR / "last_checkpoint.json").write_text(
            json.dumps(status, indent=2)
        )

    # ── Job list builder ───────────────────────────────────────────────────────

    def _build_jobs(
        self,
        systems_to_run: Optional[List[str]],
        llms: Optional[List[str]],
    ) -> List[Dict]:
        """
        Returns list of job dicts: {query, system, llm}.
        System 3 (text2cypher_finetuned) uses llm="".
        """
        if systems_to_run is None:
            systems_to_run = LLM_SYSTEMS + FIXED_SYSTEMS
        if llms is None:
            llms = DEFAULT_LLMS

        jobs = []
        for q in self.queries:
            for system in systems_to_run:
                if system in FIXED_SYSTEMS:
                    jobs.append({"query": q, "system": system, "llm": ""})
                else:
                    for llm in llms:
                        jobs.append({"query": q, "system": system, "llm": llm})
        return jobs

    # ── Single evaluation ──────────────────────────────────────────────────────

    def _run_single(
        self, query: Dict, system: str, llm: str
    ) -> Dict:
        """Generate + evaluate one (query, system, llm) triple. Returns result record."""
        nl_query    = query["nl_query"]
        gold_cypher = query.get("cypher", query.get("gold_cypher", ""))

        # ── Generate ──────────────────────────────────────────────────────────
        gen_result = None
        gen_error  = None
        last_exc   = None

        for attempt in range(QUERY_RETRIES):
            try:
                if system in FIXED_SYSTEMS:
                    gen_result = self._systems.text2cypher_finetuned(nl_query)
                elif system == "baseline":
                    gen_result = self._systems.baseline(nl_query, llm)
                elif system == "cypherbench_style":
                    gen_result = self._systems.cypherbench_style(nl_query, llm)
                elif system == "schema_plus_values":
                    gen_result = self._systems.schema_plus_values(nl_query, llm)
                elif system == "dkb_no_examples":
                    gen_result = self._systems.dkb_no_examples(nl_query, llm)
                elif system == "dkb":
                    gen_result = self._systems.dkb(nl_query, llm)
                elif system == "dkb_hybrid":
                    gen_result = self._systems.dkb_hybrid(nl_query, llm)
                else:
                    gen_result = {"generated_cypher": None, "generation_time_ms": 0,
                                  "error": f"unknown system: {system}", "prompt_used": ""}
                break  # success
            except Exception as e:
                last_exc = e
                if attempt < QUERY_RETRIES - 1:
                    time.sleep(2)
                else:
                    gen_error = f"generation_error: {str(e)[:150]}"

        if gen_result is None:
            gen_result = {
                "generated_cypher":  None,
                "generation_time_ms": 0.0,
                "error":             gen_error or "unknown",
                "prompt_used":       "",
            }

        generated_cypher = gen_result.get("generated_cypher")
        gen_time_ms      = gen_result.get("generation_time_ms", 0.0)
        gen_err          = gen_result.get("error") or gen_error

        # ── Evaluate ──────────────────────────────────────────────────────────
        if generated_cypher:
            try:
                metrics = self._evaluator.evaluate_all(
                    generated_cypher, gold_cypher, nl_query
                )
            except Exception as e:
                metrics = {
                    "CV": 0.0, "ES": 0.0, "EM": 0.0, "SE": 0.0, "RQ": 0.0,
                    "_eval_ms": 0.0, "_error": str(e)[:150],
                }
        else:
            metrics = {
                "CV": 0.0, "ES": 0.0, "EM": 0.0, "SE": 0.0, "RQ": 0.0,
                "_eval_ms": 0.0, "_error": gen_err,
            }

        eval_error = metrics.pop("_error", None)
        metrics.pop("_eval_ms", None)

        return {
            "query_id":         query["query_id"],
            "nl_query":         nl_query,
            "gold_cypher":      gold_cypher,
            "query_type":       query.get("type", query.get("query_type", "")),
            "complexity":       query.get("complexity", ""),
            "system":           system,
            "llm":              llm,
            "generated_cypher": generated_cypher,
            "metrics":          metrics,
            "generation_time_ms": gen_time_ms,
            "eval_error":       eval_error or gen_err,
            "timestamp":        datetime.now(timezone.utc).isoformat(),
        }

    # ── Main run ───────────────────────────────────────────────────────────────

    def run(
        self,
        systems_to_run: Optional[List[str]] = None,
        llms: Optional[List[str]] = None,
        results_file: Optional[str] = None,
    ) -> None:
        """
        Run the full evaluation pipeline.

        Args:
            systems_to_run: list of system names (default: all 5)
            llms: list of Ollama model tags (default: 4 selected models)
            results_file: override the output path
        """
        if results_file:
            self.results_file = Path(results_file)
            self.results_file.parent.mkdir(parents=True, exist_ok=True)
            self._done = self._load_done_set()

        jobs = self._build_jobs(systems_to_run, llms)

        total  = len(jobs)
        n_skip = sum(
            1 for j in jobs
            if (j["query"]["query_id"], j["system"], j["llm"]) in self._done
        )
        n_todo = total - n_skip

        print(f"\n{'='*60}")
        print(f"  Japan PM2.5 NL-to-Cypher Competitive Evaluation")
        print(f"  BDA 2026 — Experiment Runner")
        print(f"{'='*60}")
        print(f"  Queries    : {len(self.queries)}")
        print(f"  Systems    : {systems_to_run or LLM_SYSTEMS + FIXED_SYSTEMS}")
        print(f"  LLMs       : {llms or DEFAULT_LLMS}")
        print(f"  Total jobs : {total:,}")
        print(f"  Already done (skip): {n_skip:,}")
        print(f"  To run     : {n_todo:,}")
        print(f"  Results    → {self.results_file}")
        print()

        n_done_session = 0
        se_running     = 0.0
        n_se_scored    = 0
        bar = tqdm(
            jobs,
            total=total,
            initial=n_skip,
            desc="Eval",
            unit="eval",
            dynamic_ncols=True,
        )

        for job in bar:
            q      = job["query"]
            system = job["system"]
            llm    = job["llm"]
            qid    = q["query_id"]
            key    = (qid, system, llm)

            if key in self._done:
                continue

            short_llm = llm.split(":")[0][:10] if llm else "ft-model"
            bar.set_description(f"{system[:12]}|{short_llm}|{qid}")

            # Run with graceful skip on total failure
            try:
                record = self._run_single(q, system, llm)
            except Exception as e:
                # Graceful skip: write a failed record
                record = {
                    "query_id":         qid,
                    "nl_query":         q["nl_query"],
                    "gold_cypher":      q.get("cypher", ""),
                    "query_type":       q.get("type", ""),
                    "complexity":       q.get("complexity", ""),
                    "system":           system,
                    "llm":              llm,
                    "generated_cypher": None,
                    "metrics":          {"CV": 0.0, "ES": 0.0, "EM": 0.0, "SE": 0.0, "RQ": 0.0},
                    "generation_time_ms": 0.0,
                    "eval_error":       f"runner_exception: {str(e)[:150]}",
                    "timestamp":        datetime.now(timezone.utc).isoformat(),
                }

            self._append(record)
            self._done.add(key)
            n_done_session += 1

            # SE may be None (gold query un-evaluable: timeout / invalid gold) —
            # such queries are excluded from the SE mean rather than counted as 0.
            sev = record["metrics"].get("SE")
            if isinstance(sev, (int, float)):
                se_running += sev
                n_se_scored += 1

            # Print running avg SE every 100 evaluations
            if n_done_session % PRINT_SE_EVERY == 0:
                avg_se = se_running / n_se_scored if n_se_scored else 0.0
                bar.write(
                    f"\n  [SE avg @ {n_done_session}/{n_todo}] "
                    f"SE={avg_se:.4f} (n={n_se_scored})  system={system}  llm={short_llm}\n"
                )

            # Checkpoint every 50 evaluations
            if n_done_session % CHECKPOINT_N == 0:
                self._save_checkpoint(len(self._done))

        # Final checkpoint
        self._save_checkpoint(len(self._done))
        self._evaluator.close()

        avg_se = se_running / n_se_scored if n_se_scored > 0 else 0.0
        print(f"\nDone. {n_done_session} new evaluations → {self.results_file}")
        print(f"Session avg SE: {avg_se:.4f} (scored on {n_se_scored} queries with evaluable gold)")


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run PM2.5 NL-to-Cypher competitive evaluation"
    )
    parser.add_argument("--systems", nargs="+", default=None, help="Systems to run")
    parser.add_argument("--llms",    nargs="+", default=None, help="LLMs to use")
    parser.add_argument(
        "--results-file", default=str(DEFAULT_RESULTS),
        help="Output JSONL file"
    )
    parser.add_argument(
        "--benchmark", default=str(BENCHMARK_PATH),
        help="Benchmark JSON file (e.g. a curated clean-gold subset)"
    )
    parser.add_argument("--n", type=int, default=None, help="Limit to first N queries")
    parser.add_argument("--exec-timeout", type=float, default=QUERY_TIMEOUT_S,
                        help="Per-query Neo4j execution timeout in seconds")
    args = parser.parse_args()

    runner = ExperimentRunner(results_file=args.results_file, benchmark_path=args.benchmark,
                              exec_timeout_s=args.exec_timeout)
    if args.n:
        runner.queries = runner.queries[: args.n]

    runner.run(systems_to_run=args.systems, llms=args.llms)
