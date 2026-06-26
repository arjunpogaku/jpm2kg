"""
evaluator.py — 5-metric evaluation suite for NL-to-Cypher quality assessment.

Class QueryEvaluator:
  cv(generated_cypher)                              → float  Cypher Validity (0/1)
  es(generated_cypher)                              → float  Execution Success (0/1)
  em(generated_cypher, gold_cypher)                 → float  Exact Match (0/1)
  se(generated_cypher, gold_cypher, neo4j_driver)   → float  Semantic Equivalence (0/1)
  rq(generated_cypher, gold_cypher, nl_query)       → float  Result Quality (0–1)
  evaluate_all(generated_cypher, gold_cypher, nl_query) → dict  all 5 metrics
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from neo4j import GraphDatabase, Query
from neo4j.exceptions import CypherSyntaxError, ClientError, DatabaseError

# ── Neo4j connection config ────────────────────────────────────────────────────

NEO4J_URI  = "bolt://localhost:37689"
NEO4J_USER = "neo4j"
NEO4J_PASS = "StrongPasswordHere"
EXEC_TIMEOUT_S = 30   # seconds before treating execution as failure

# Neo4j error codes that indicate a genuine syntax / schema problem
_FATAL_CV_CODES = {
    "Neo.ClientError.Statement.SyntaxError",
    "Neo.ClientError.Schema.TokenNameError",
}
_FATAL_CV_MESSAGES = (
    "invalid input",
    "unknown label",
    "unknown relationship",
    "unknown variable",
    "type mismatch",
    "syntaxexception",
)

# JAPAQ-KG schema (the four real node labels and relationship types). Used to
# enforce *schema compliance* in CV. This is required because Neo4j 5/6 downgrade
# "label/relationship does not exist" from an error to a mere notification — so an
# EXPLAIN of `MATCH (m:Measurement)-[:HAS_READING]->()` SUCCEEDS, and CV based on
# EXPLAIN alone cannot distinguish real schema from a hallucinated one.
_VALID_SCHEMA_NAMES = {
    "Station", "Location", "ObservationTime", "ObservedPM25",   # node labels
    "LOCATED_AT", "AT_LOCATION", "OBSERVED_AT", "RECORDED_BY",  # relationship types
}
# Capture `:Name` where Name starts uppercase. In this schema both node labels
# (PascalCase) and relationship types (UPPER_CASE) start uppercase, while
# property-map keys are lowercase (`{prefecture_en: ...}`) and string values are
# quoted — so this cleanly separates schema references from data/properties.
_SCHEMA_REF_RE = re.compile(r":\s*([A-Z][A-Za-z0-9_]*)")


class QueryEvaluator:
    """
    Evaluates generated Cypher queries against gold standard using 5 metrics.
    Uses a shared Neo4j driver; call close() when done.
    """

    def __init__(
        self,
        neo4j_uri: str = NEO4J_URI,
        neo4j_user: str = NEO4J_USER,
        neo4j_pass: str = NEO4J_PASS,
        exec_timeout_s: float = EXEC_TIMEOUT_S,
    ):
        self._driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
        self._exec_timeout_s = exec_timeout_s
        # Cache of cypher_text -> (success, rows, error). A single gold query
        # (which may take 100s+) is therefore executed at most once across all
        # systems and all metrics in a run, instead of 3x per (system, query).
        self._exec_cache: Dict[str, Tuple[bool, Optional[List[Dict]], Optional[str]]] = {}

    def close(self):
        """Close the Neo4j driver connection."""
        try:
            self._driver.close()
        except Exception:
            pass

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _run_query(
        self, cypher: str, limit: int = 200
    ) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Execute a Cypher query with a server-side transaction timeout.
        Returns (success: bool, rows: list|None, error: str|None).
        Appends LIMIT if not present. Caps result at `limit` rows.

        Results are cached by query text: gold queries (some scan 71M nodes and
        take >100s) are reused across systems/metrics instead of re-executed.

        NOTE: the transaction timeout MUST be set via the neo4j ``Query`` object.
        Passing ``timeout=`` to ``session.run(text, timeout=...)`` is silently
        treated as a *Cypher parameter* named ``timeout`` and has no effect —
        this was the original cause of the multi-minute hangs.
        """
        if not cypher or not cypher.strip():
            return False, None, "empty query"

        cached = self._exec_cache.get(cypher)
        if cached is not None:
            return cached

        safe = cypher if re.search(r"\bLIMIT\b", cypher, re.IGNORECASE) else cypher + f" LIMIT {limit}"
        try:
            with self._driver.session() as session:
                result = session.run(Query(safe, timeout=self._exec_timeout_s))
                rows   = result.fetch(limit)
            out = (True, [dict(r) for r in rows], None)
        except CypherSyntaxError as e:
            out = (False, None, f"SyntaxError: {str(e)[:150]}")
        except ClientError as e:
            # Transaction timeout surfaces here as a ClientError
            code = getattr(e, "code", "") or ""
            if "TransactionTimedOut" in code:
                out = (False, None, f"Timeout: exceeded {self._exec_timeout_s}s")
            else:
                out = (False, None, f"ClientError: {str(e)[:150]}")
        except DatabaseError as e:
            out = (False, None, f"DatabaseError: {str(e)[:150]}")
        except Exception as e:
            out = (False, None, f"{type(e).__name__}: {str(e)[:150]}")

        self._exec_cache[cypher] = out
        return out

    # ── Result-set normalization for Semantic Equivalence ──────────────────────

    @staticmethod
    def _norm_value(v: Any) -> Any:
        """
        Normalize a single result cell to a comparable primitive:
          - int/float       → float rounded to 2 dp (unifies 193 vs 193.0,
                              and round(avg,2) vs un-rounded aggregates)
          - bool            → kept as bool (before int check)
          - str             → stripped, casefolded
          - None            → sentinel '∅'
          - Neo4j node/rel / dict / list (non-primitive) → None (ignored)
        """
        if v is None:
            return "∅"
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            try:
                return round(float(v), 2)
            except (ValueError, OverflowError):
                return float("nan")
        if isinstance(v, str):
            return v.strip().casefold()
        # Node objects, relationships, maps, lists → not a primitive answer value
        return None

    @classmethod
    def _value_multiset(cls, rows: Optional[List[Dict]]) -> List[Any]:
        """
        Flatten a result set into a multiset of normalized primitive *values*,
        DISCARDING column names. This makes SE robust to:
          - arbitrary column aliases  (hours_exceeded vs exceeded_hours)
          - column ordering
          - int/float and rounding differences
        Non-primitive cells (node objects) are dropped.
        """
        vals: List[Any] = []
        for r in (rows or [])[:200]:
            for v in r.values():
                nv = cls._norm_value(v)
                if nv is not None:
                    vals.append(nv)
        return vals

    @staticmethod
    def _multiset_f1(gen: List[Any], gold: List[Any]) -> float:
        """
        F1 overlap between two value multisets (order-independent, with
        multiplicity). Generalizes 'intersection / gold' (recall) into a
        symmetric score that also penalizes spurious extra values (precision).
        Both empty → 1.0.
        """
        from collections import Counter
        cg, cgold = Counter(gen), Counter(gold)
        if not cg and not cgold:
            return 1.0
        inter = sum((cg & cgold).values())
        if inter == 0:
            return 0.0
        precision = inter / max(1, sum(cg.values()))
        recall    = inter / max(1, sum(cgold.values()))
        return round(2 * precision * recall / (precision + recall), 4)

    @staticmethod
    def _normalize_cypher(cypher: str) -> str:
        """Normalize Cypher for exact match: lowercase, collapse whitespace, strip comments."""
        if not cypher:
            return ""
        c = cypher.lower().strip()
        c = re.sub(r"//[^\n]*", "", c)   # remove inline comments
        c = re.sub(r"\s+", " ", c)        # collapse whitespace
        return c.strip()

    # ── Metric 1: Cypher Validity (CV) ────────────────────────────────────────

    @staticmethod
    def _schema_compliant(cypher: str) -> bool:
        """
        True iff every PascalCase/UPPER `:Name` schema reference in the query is a
        real JAPAQ-KG label or relationship type. Catches hallucinated schema
        (e.g. :Measurement, :Prefecture, :HAS_READING) that Neo4j 5/6 only *warns*
        about, so EXPLAIN alone would wrongly pass it.
        """
        refs = set(_SCHEMA_REF_RE.findall(cypher or ""))
        if not refs:
            return False  # a query that references no real label/rel is not valid
        return refs.issubset(_VALID_SCHEMA_NAMES)

    def cv(self, generated_cypher: str) -> float:
        """
        Cypher Validity: 1.0 iff the query (a) parses (EXPLAIN succeeds, ignoring
        property-key / index notifications) AND (b) is *schema compliant* — it
        uses only the four real node labels and four real relationship types.

        Both conditions are required. EXPLAIN catches grammar errors; the schema
        check catches hallucinated labels/relationships, which modern Neo4j
        downgrades to non-fatal notifications (so EXPLAIN alone would pass e.g.
        `MATCH (m:Measurement)-[:HAS_READING]->()`).

        CV is about syntax + schema structure, NOT whether the query returns
        correct data (that is ES / SE).
        """
        if not generated_cypher or not generated_cypher.strip():
            return 0.0

        # (b) schema compliance
        if not self._schema_compliant(generated_cypher):
            return 0.0

        # (a) parseability
        try:
            with self._driver.session() as session:
                session.run(f"EXPLAIN {generated_cypher}").consume()
            return 1.0

        except CypherSyntaxError:
            return 0.0

        except ClientError as e:
            code = getattr(e, "code", "") or ""
            msg  = str(e).lower()
            if code in _FATAL_CV_CODES:
                return 0.0
            if any(pat in msg for pat in _FATAL_CV_MESSAGES):
                return 0.0
            return 1.0

        except DatabaseError:
            return 0.0

        except Exception:
            return 0.0

    # ── Metric 2: Execution Success (ES) ──────────────────────────────────────

    def es(self, generated_cypher: str) -> float:
        """
        Execution Success: 1.0 if the query runs without error within 30s timeout,
        0.0 otherwise.
        """
        if not generated_cypher or not generated_cypher.strip():
            return 0.0
        success, _, _ = self._run_query(generated_cypher)
        return 1.0 if success else 0.0

    # ── Metric 3: Exact Match (EM) ────────────────────────────────────────────

    def em(self, generated_cypher: str, gold_cypher: str) -> float:
        """
        Exact Match: 1.0 if normalized generated == normalized gold, 0.0 otherwise.
        Normalization: lowercase, strip whitespace, remove inline comments.
        """
        return 1.0 if (
            self._normalize_cypher(generated_cypher) ==
            self._normalize_cypher(gold_cypher)
        ) else 0.0

    # ── Metric 4: Semantic Equivalence (SE) ───────────────────────────────────

    def se(
        self,
        generated_cypher: str,
        gold_cypher: str,
        neo4j_driver=None,  # accepted for API compatibility; uses self._driver
    ) -> Optional[float]:
        """
        Semantic Equivalence with partial credit (0.0–1.0), or None if the gold
        query itself cannot be evaluated.

        Compares the *value content* of the two result sets — F1 overlap of the
        normalized primitive-value multisets — rather than requiring byte-identical
        rows. This is robust to:
          - column aliasing      (gold 'hours_exceeded' vs gen 'exceeded_hours')
          - column / row ordering
          - int vs float and rounding (round(avg,2) vs raw)
          - gold queries that echo question constants back as extra columns

        Returns:
          None  if gold cannot execute (syntax error / timeout) — query is then
                excluded from SE aggregation rather than unfairly scoring the
                system 0 for a broken gold.
          0.0   if the generated query fails / is empty.
          F1∈(0,1]  value-overlap between generated and gold result sets.
        """
        # Establish gold viability FIRST. If the reference can't run, SE is undefined.
        gold_ok, gold_rows, _ = self._run_query(gold_cypher)
        if not gold_ok:
            return None

        if not generated_cypher or not generated_cypher.strip():
            return 0.0
        gen_ok, gen_rows, _ = self._run_query(generated_cypher)
        if not gen_ok:
            return 0.0

        gen_vals  = self._value_multiset(gen_rows)
        gold_vals = self._value_multiset(gold_rows)
        return self._multiset_f1(gen_vals, gold_vals)

    # ── Metric 5: Result Quality (RQ) ─────────────────────────────────────────

    def rq(
        self,
        generated_cypher: str,
        gold_cypher: str,
        nl_query: str,
    ) -> float:
        """
        Result Quality heuristic (0.0–1.0):
          +0.5  if execution returns a non-empty result set when gold is non-empty
                (or both empty — empty for empty counts as good)
          +0.5  if result entity type matches query intent
                (inferred from key terms in nl_query vs returned column names)
        """
        if not generated_cypher or not generated_cypher.strip():
            return 0.0

        gen_ok, gen_rows, _ = self._run_query(generated_cypher)
        if not gen_ok:
            return 0.0

        _, gold_rows, _ = self._run_query(gold_cypher)

        score = 0.0

        # +0.5 for non-empty match or both-empty match
        gen_empty  = (gen_rows is None or len(gen_rows) == 0)
        gold_empty = (gold_rows is None or len(gold_rows) == 0)

        if gold_empty and gen_empty:
            score += 0.5   # both empty: expected
        elif not gold_empty and not gen_empty:
            score += 0.5   # both non-empty: acceptable

        # +0.5 for entity type matching query intent
        nl_lower = nl_query.lower()
        gen_cols = set()
        if gen_rows:
            gen_cols = set(gen_rows[0].keys())

        # Heuristic: check if column names correlate with query intent keywords
        intent_col_map = {
            "station":      {"station", "stationname", "stationname_en"},
            "prefecture":   {"prefecture", "prefecture_en"},
            "average":      {"avg", "average", "avg_pm25", "mean"},
            "count":        {"count", "total", "n", "num"},
            "max":          {"max", "maximum", "max_pm25"},
            "min":          {"min", "minimum", "min_pm25"},
            "location":     {"location", "prefecture_en", "city"},
            "season":       {"season"},
            "year":         {"year"},
            "level":        {"level", "pm25_level"},
        }
        matched_intent = False
        for kw, col_set in intent_col_map.items():
            if kw in nl_lower and gen_cols & col_set:
                matched_intent = True
                break

        if not matched_intent and gen_cols:
            # Fallback: any column overlap with gold columns
            gold_cols = set(gold_rows[0].keys()) if gold_rows else set()
            if gen_cols & gold_cols:
                matched_intent = True

        if matched_intent:
            score += 0.5

        return round(score, 4)

    # ── All metrics ────────────────────────────────────────────────────────────

    def evaluate_all(
        self,
        generated_cypher: str,
        gold_cypher: str,
        nl_query: str,
    ) -> Dict[str, Any]:
        """
        Run all 5 metrics. Returns:
            {
                "CV": float, "ES": float, "EM": float, "SE": float, "RQ": float,
                "_eval_ms": float, "_error": str|None,
            }
        """
        t0    = time.time()
        error = None

        try:
            cv_score = self.cv(generated_cypher)
            es_score = self.es(generated_cypher)
            em_score = self.em(generated_cypher, gold_cypher)
            se_score = self.se(generated_cypher, gold_cypher)
            rq_score = self.rq(generated_cypher, gold_cypher, nl_query)
        except Exception as e:
            error    = str(e)[:200]
            cv_score = es_score = em_score = se_score = 0.0
            rq_score = 0.0

        return {
            "CV":       cv_score,
            "ES":       es_score,
            "EM":       em_score,
            "SE":       se_score,
            "RQ":       rq_score,
            "_eval_ms": round((time.time() - t0) * 1000, 2),
            "_error":   error,
        }


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ev = QueryEvaluator()
    gold = (
        "MATCH (p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime)-[:AT_LOCATION]->(l:Location)\n"
        "WHERE l.prefecture_en = 'Aichi Prefecture'\n"
        "  AND t.season = 'Winter'\n"
        "  AND p.pm25 >= 0 AND p.pm25 <= 500\n"
        "RETURN l.prefecture_en AS prefecture, t.season AS season,\n"
        "       round(avg(p.pm25), 2) AS avg_pm25, count(p) AS readings"
    )
    nl = "Average PM2.5 in Aichi Prefecture during winter?"
    tests = [
        ("exact match", gold),
        ("wrong label", "MATCH (n:BadLabel) RETURN n LIMIT 5"),
        ("empty", ""),
    ]
    for name, cypher in tests:
        metrics = ev.evaluate_all(cypher, gold, nl)
        print(
            f"[{name}] CV={metrics['CV']} ES={metrics['ES']} "
            f"EM={metrics['EM']} SE={metrics['SE']} RQ={metrics['RQ']} "
            f"({metrics['_eval_ms']:.0f}ms)"
        )
    ev.close()
