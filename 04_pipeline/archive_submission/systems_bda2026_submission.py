"""
systems.py — 5 NL-to-Cypher generation systems for Japan PM2.5 KG.

Class QueryGenerationSystems with 5 methods:
  1. baseline          — zero-shot prompt
  2. cypherbench_style — dynamic schema from Neo4j (CypherBench, Feng et al. ACL 2025)
  3. text2cypher_finetuned — HuggingFace neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1
  4. dkb               — DKB domain knowledge base prompt
  5. dkb_hybrid        — DKB + top-3 retrieved examples via sentence-transformers

All methods return:
    {
        "generated_cypher": str | None,
        "generation_time_ms": float,
        "error": str | None,
        "prompt_used": str,
    }

References:
    CypherBench (Feng et al., ACL 2025): schema-grounded Cypher generation
    T2CSS (ScienceDirect 2025): semantic schema + domain knowledge
"""

from __future__ import annotations

import os
# Force transformers/sentence-transformers to use the PyTorch backend.
# Without this, `import sentence_transformers` crashes under Keras 3
# ("not yet supported in Transformers"), which silently disabled DKB-Hybrid's
# semantic retrieval (it fell back to static examples). Must be set before
# any transformers import.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import requests

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Constants ──────────────────────────────────────────────────────────────────

OLLAMA_URL     = "http://localhost:11434"
# Per-call timeout (seconds). Overridable via env for large models (70B/72B are
# slow on long prompts; the default 60s can spuriously time out CypherBench/DKB).
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "60"))
OLLAMA_RETRIES = 2

NEO4J_URI  = "bolt://localhost:37689"
NEO4J_USER = "neo4j"
NEO4J_PASS = "StrongPasswordHere"

DKB_PATH = Path("/home/arjun/pm25_system/data/dkb_japan.json")

_dkb_cache: Optional[dict] = None
_st_model_cache = None        # sentence-transformers model (lazy)
_st_embeddings_cache: Optional[dict] = None  # {pattern_id: (embedding, pattern_dict)}


# ── Ollama helper ──────────────────────────────────────────────────────────────

def _call_ollama(model: str, prompt: str, timeout: int = OLLAMA_TIMEOUT) -> str:
    # num_ctx caps the context window. Without it, large models load with their
    # huge default (llama3.1 = 131072), whose KV-cache balloons a 70B model to
    # ~120GB and spills onto CPU (very slow). Our prompts are <~2500 tokens, so an
    # 8K window is ample and does not change outputs — it just keeps the model on GPU.
    payload = {
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "think":   False,
        "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "30m"),
        "options": {"temperature": 0.0, "num_predict": 512,
                    "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "8192"))},
    }
    last_err = None
    for attempt in range(OLLAMA_RETRIES):
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except requests.Timeout:
            last_err = f"Ollama timeout ({timeout}s) for model {model}"
        except Exception as e:
            last_err = str(e)
        if attempt < OLLAMA_RETRIES - 1:
            time.sleep(1)
    raise RuntimeError(last_err or "Ollama call failed")


# ── Cypher extraction helper ───────────────────────────────────────────────────

def _extract_cypher(text: str) -> str:
    """
    Extract clean Cypher from LLM output.

    Steps:
    1. Strip markdown code fences.
    2. Find the first line that opens a Cypher statement.
    3. Collect lines until we hit prose (explanation text).
    4. On the last collected line, truncate anything after the last
       Cypher terminator (semicolon, LIMIT clause, RETURN clause)
       so that mid-line prose like "LIMIT 100; Let me explain..." is cut.
    """
    if not text:
        return ""

    # 0. Unescape literal escape sequences. Some models (notably the fine-tuned
    #    neo4j-gemma) emit Cypher as a single line containing literal "\n"/"\t"
    #    (backslash-n), which Neo4j rejects with "Invalid input '\'". Only do
    #    this when there are escapes but essentially no real newlines, so we
    #    never corrupt already well-formed multi-line Cypher.
    if "\\n" in text and text.count("\n") <= 1:
        text = (text.replace("\\r\\n", "\n").replace("\\n", "\n")
                    .replace("\\t", " ").replace('\\"', '"').replace("\\'", "'"))

    # 1. Strip markdown fences and common lead-ins ("Cypher:", "Answer:", "Query:")
    text = re.sub(r"```(?:cypher)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    text = re.sub(r"^\s*(cypher|answer|query|sql)\s*:\s*", "", text,
                  flags=re.IGNORECASE)

    lines = text.strip().splitlines()

    _CYPHER_START = re.compile(
        r"^\s*(MATCH|WITH|CALL|RETURN|MERGE|CREATE|OPTIONAL|UNWIND|WHERE|FOREACH)",
        re.IGNORECASE,
    )
    _PROSE_LINE = re.compile(
        r"^\s*("
        r"\*+|"          # markdown bold/bullets: **Explanation:**, * item
        r"#+\s|"          # markdown headers
        r"\d+\.\s|"       # numbered explanation lists: "1. **MATCH ...**"
        r"-\s|"           # markdown dash bullets
        r">|"             # blockquotes
        r"This |Note:?|The query|In this|Here|Explanation|Output|Result|"
        r"Let me|I |We |As you|You can|To )",
        re.IGNORECASE,
    )

    # 2. Find first Cypher line
    start = None
    for i, line in enumerate(lines):
        if _CYPHER_START.match(line):
            start = i
            break
    if start is None:
        return ""

    # 3. Collect lines, stopping at prose
    cypher_lines: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            # blank line — look ahead; stop if next non-blank is prose
            rest = [l for l in lines[lines.index(line) + 1:] if l.strip()]
            if rest and _PROSE_LINE.match(rest[0]):
                break
            cypher_lines.append(line)
        elif _PROSE_LINE.match(line) and cypher_lines:
            break
        else:
            cypher_lines.append(line)

    if not cypher_lines:
        return ""

    # 4. Truncate mid-line prose on the last line after a Cypher terminator.
    #    Matches:  "... LIMIT 100; Let me explain"  → keep up to "LIMIT 100"
    #              "... RETURN s\n\nLet me..."       → already handled above
    _TERMINATOR = re.compile(
        r"(;|(?<=\S)\s*LIMIT\s+\d+|(?<=\w)\s*RETURN\b[^;]*?)(\s*[;]?\s*(?:Let me|Note|This|#).*)$",
        re.IGNORECASE,
    )
    last = cypher_lines[-1]
    # Simple approach: if a semicolon appears and is followed by non-Cypher text, cut there
    if ";" in last:
        parts = last.split(";", 1)
        after = parts[1].strip()
        # If what follows the semicolon looks like prose (starts with a word, not a Cypher keyword)
        if after and not re.match(r"^\s*(MATCH|WITH|CALL|RETURN|WHERE|LIMIT|ORDER|SKIP)", after, re.IGNORECASE):
            cypher_lines[-1] = parts[0].rstrip()

    return "\n".join(cypher_lines).strip()


# ── Result dict builder ────────────────────────────────────────────────────────

def _result(
    cypher: Optional[str],
    elapsed_ms: float,
    prompt: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "generated_cypher":  cypher,
        "generation_time_ms": round(elapsed_ms, 2),
        "error":             error,
        "prompt_used":       prompt,
    }


# ── DKB loader ─────────────────────────────────────────────────────────────────

def _load_dkb() -> dict:
    global _dkb_cache
    if _dkb_cache is None:
        _dkb_cache = json.loads(DKB_PATH.read_text())
    return _dkb_cache


# ── Sentence-transformers for dkb_hybrid ──────────────────────────────────────

def _get_st_model():
    global _st_model_cache
    if _st_model_cache is None:
        try:
            from sentence_transformers import SentenceTransformer
            _st_model_cache = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _st_model_cache


def _build_st_embeddings():
    """Build sentence-transformers embeddings for all DKB query patterns (lazy)."""
    global _st_embeddings_cache
    if _st_embeddings_cache is not None:
        return
    dkb      = _load_dkb()
    patterns = dkb["query_patterns"]
    model    = _get_st_model()
    cache    = {}
    texts    = [p.get("nl_example", p.get("nl_template", "")) for p in patterns]
    embeddings = model.encode(texts, normalize_embeddings=True)
    for i, p in enumerate(patterns):
        cache[p["pattern_id"]] = (embeddings[i], p)
    _st_embeddings_cache = cache


def _retrieve_top_k(nl_query: str, k: int = 3) -> list[dict]:
    """Return top-k DKB patterns by cosine similarity (sentence-transformers)."""
    _build_st_embeddings()
    model   = _get_st_model()
    q_vec   = model.encode([nl_query], normalize_embeddings=True)[0]
    ids     = list(_st_embeddings_cache.keys())
    matrix  = np.stack([_st_embeddings_cache[pid][0] for pid in ids])
    scores  = matrix @ q_vec
    top_idx = np.argsort(scores)[::-1][:k].tolist()
    return [_st_embeddings_cache[ids[i]][1] for i in top_idx]


# ── Neo4j schema fetcher for cypherbench_style ────────────────────────────────

def _fetch_neo4j_schema() -> str:
    """
    Dynamically fetch schema from Neo4j.
    Queries node labels, properties, and relationship types.
    """
    try:
        from neo4j import GraphDatabase, Query
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        schema_parts = []

        # Only the Japan PM2.5 labels (the DB also holds a parallel US graph).
        JP_LABELS = {"Station", "Location", "ObservationTime", "ObservedPM25"}

        with driver.session() as session:
            # Node labels
            labels_result = session.run("CALL db.labels() YIELD label RETURN label")
            labels = [r["label"] for r in labels_result if r["label"] in JP_LABELS]

            # Properties per label. IMPORTANT: sample a bounded set of nodes BEFORE
            # UNWIND. `... UNWIND keys(n) RETURN DISTINCT k LIMIT 50` scans ALL nodes
            # when the true distinct-key count (<10) never reaches the LIMIT — on the
            # 71M-node labels that is a multi-minute full scan (the schema-fetch hang).
            node_info = []
            for label in labels:
                props_result = session.run(Query(
                    f"MATCH (n:`{label}`) WITH n LIMIT 500 "
                    f"UNWIND keys(n) AS k RETURN DISTINCT k",
                    timeout=15.0,
                ))
                props = [r["k"] for r in props_result]
                node_info.append(f"  ({label}) properties: {props}")

            # Relationship types
            rel_result = session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            rel_types = [r["relationshipType"] for r in rel_result]

            # Relationship patterns (only those connecting Japan labels)
            JP_RELS = {"LOCATED_AT", "AT_LOCATION", "OBSERVED_AT", "RECORDED_BY"}
            rel_types = [rt for rt in rel_types if rt in JP_RELS]
            rel_patterns = []
            for rt in rel_types:
                try:
                    pat_result = session.run(Query(
                        f"MATCH (a)-[r:`{rt}`]->(b) "
                        f"RETURN DISTINCT labels(a)[0] AS src, labels(b)[0] AS tgt LIMIT 1",
                        timeout=15.0,
                    ))
                    for row in pat_result:
                        if row["src"] and row["tgt"]:
                            rel_patterns.append(
                                f"  (:{row['src']})-[:{rt}]->(:{row['tgt']})"
                            )
                except Exception:
                    rel_patterns.append(f"  [:{rt}]")

        driver.close()

        schema_parts.append("Node Labels and Properties:")
        schema_parts.extend(node_info)
        schema_parts.append("\nRelationship Types:")
        schema_parts.extend(rel_patterns)
        return "\n".join(schema_parts)

    except Exception as e:
        # Fallback to static schema from DKB
        dkb    = _load_dkb()
        actual = dkb.get("kg_actual_schema", {})
        lines  = ["Node Labels and Properties (static fallback):"]
        for lbl, info in actual.get("node_labels", {}).items():
            props = actual.get("property_keys", {}).get(lbl, [])
            lines.append(f"  ({lbl}) properties: {props}")
        lines.append("\nRelationship Types:")
        for rt, info in actual.get("relationship_types", {}).items():
            lines.append(f"  {info.get('pattern', rt)}")
        return "\n".join(lines) + f"\n[Schema fetched from static DKB; Neo4j error: {e}]"


# ── DKB prompt sections ────────────────────────────────────────────────────────

def _build_dkb_prompt_core(nl_query: str, extra_examples: Optional[list] = None) -> str:
    """Build the DKB-based prompt. extra_examples are prepended to DKB query_patterns."""
    dkb    = _load_dkb()
    actual = dkb.get("kg_actual_schema", {})

    # Schema specification from DKB
    schema_spec = dkb.get("schema_specification", {})
    node_lines  = []
    for lbl in actual.get("node_labels", {}):
        props = actual.get("property_keys", {}).get(lbl, [])
        node_lines.append(f"  ({lbl}) properties: {props}")
    rel_lines = []
    for rt, info in actual.get("relationship_types", {}).items():
        rel_lines.append(f"  {info.get('pattern', rt)}")

    schema_text = (
        "Node Labels:\n" + "\n".join(node_lines) +
        "\n\nRelationships:\n" + "\n".join(rel_lines)
    )

    # Canonical traversal from DKB
    canonical = actual.get("canonical_traversal", "")
    enum_vals  = actual.get("enum_values", {})
    enum_lines = [f"  {k}: {v}" for k, v in enum_vals.items()]

    # PM2.5 health rules
    pm25_lines = []
    for r in dkb.get("pm25_health_rules", [])[:6]:
        cf = r.get("cypher_filter") or r.get("cypher_level_filter") or r.get("cypher_numeric_filter", "")
        pm25_lines.append(f"  [{r.get('rule_id','')}] {r.get('name','')}: {r.get('description','')[:80]}")
        if cf:
            pm25_lines.append(f"    Cypher: {cf}")

    # Temporal rules
    temp_lines = []
    for r in dkb.get("temporal_rules", [])[:8]:
        cf = r.get("cypher_season_filter") or r.get("cypher_filter", "")
        temp_lines.append(f"  {r.get('name', '')}: {cf}")

    # Traversal policies
    policy_lines = []
    for p in dkb.get("traversal_policies", [])[:4]:
        good = p.get("good_pattern", p.get("cypher_pattern", ""))
        policy_lines.append(f"  [{p.get('priority','')}] {p.get('description','')}")
        if good:
            policy_lines.append(f"    Use: {good}")

    # Query pattern examples
    patterns_to_show = list(extra_examples or []) + dkb.get("query_patterns", [])[:8]
    example_lines = []
    for p in patterns_to_show[:8]:
        example_lines.append(f"# {p.get('intent','')}")
        example_lines.append(f"# Q: {p.get('nl_example', p.get('nl_template',''))}")
        example_lines.append(p.get("cypher", ""))
        example_lines.append("")

    prompt = f"""You are a Cypher expert for a Japan PM2.5 air quality knowledge graph.

<schema_specification>
{schema_text}

Canonical traversal:
  {canonical}

Enum values (use EXACTLY as shown):
{chr(10).join(enum_lines)}
</schema_specification>

<pm25_health_rules>
{chr(10).join(pm25_lines)}
</pm25_health_rules>

<temporal_rules>
{chr(10).join(temp_lines)}
</temporal_rules>

<traversal_policies>
{chr(10).join(policy_lines)}
</traversal_policies>

<critical_rules>
- Location.prefecture_en format: 'Aichi Prefecture' (NOT 'Aichi' — always append ' Prefecture')
- ObservationTime.season values: 'Spring' | 'Summer' | 'Autumn' | 'Winter'
- ObservationTime.dayType values: 'Weekday' | 'Weekend'
- Station.stationtype_en values: 'General Station' | 'Roadside Station'
- ObservedPM25.pm25_level: 'Safe' | 'Moderate' | 'Slightly Unhealthy' | 'Unhealthy' | 'Very Unhealthy'
- Always add validity filter: WHERE p.pm25 >= 0 AND p.pm25 <= 500
- Do NOT use labels: Prefecture, Statistics, PM25Measurement, HAS_STATS, LOCATED_IN
</critical_rules>

<query_patterns>
{chr(10).join(example_lines)}
</query_patterns>

<query>{nl_query}</query>

Cypher:"""
    return prompt


def _build_dkb_prompt_no_examples(nl_query: str) -> str:
    """
    DKB prompt with ALL sections EXCEPT query_patterns.
    Keeps: schema, enum values, pm25_health_rules, temporal_rules,
           traversal_policies, critical_rules.
    Removes: query_patterns (the 8 hardcoded Cypher examples).
    Used for Baseline E (DKB-no-examples ablation).
    """
    dkb    = _load_dkb()
    actual = dkb.get("kg_actual_schema", {})

    node_lines = []
    for lbl in actual.get("node_labels", {}):
        props = actual.get("property_keys", {}).get(lbl, [])
        node_lines.append(f"  ({lbl}) properties: {props}")
    rel_lines = []
    for rt, info in actual.get("relationship_types", {}).items():
        rel_lines.append(f"  {info.get('pattern', rt)}")

    schema_text = (
        "Node Labels:\n" + "\n".join(node_lines) +
        "\n\nRelationships:\n" + "\n".join(rel_lines)
    )

    canonical  = actual.get("canonical_traversal", "")
    enum_vals  = actual.get("enum_values", {})
    enum_lines = [f"  {k}: {v}" for k, v in enum_vals.items()]

    pm25_lines = []
    for r in dkb.get("pm25_health_rules", [])[:6]:
        cf = r.get("cypher_filter") or r.get("cypher_level_filter") or r.get("cypher_numeric_filter", "")
        pm25_lines.append(f"  [{r.get('rule_id','')}] {r.get('name','')}: {r.get('description','')[:80]}")
        if cf:
            pm25_lines.append(f"    Cypher: {cf}")

    temp_lines = []
    for r in dkb.get("temporal_rules", [])[:8]:
        cf = r.get("cypher_season_filter") or r.get("cypher_filter", "")
        temp_lines.append(f"  {r.get('name', '')}: {cf}")

    policy_lines = []
    for p in dkb.get("traversal_policies", [])[:4]:
        good = p.get("good_pattern", p.get("cypher_pattern", ""))
        policy_lines.append(f"  [{p.get('priority','')}] {p.get('description','')}")
        if good:
            policy_lines.append(f"    Use: {good}")

    # NO query_patterns section — that is the only difference from _build_dkb_prompt_core
    prompt = f"""You are a Cypher expert for a Japan PM2.5 air quality knowledge graph.

<schema_specification>
{schema_text}

Canonical traversal:
  {canonical}

Enum values (use EXACTLY as shown):
{chr(10).join(enum_lines)}
</schema_specification>

<pm25_health_rules>
{chr(10).join(pm25_lines)}
</pm25_health_rules>

<temporal_rules>
{chr(10).join(temp_lines)}
</temporal_rules>

<traversal_policies>
{chr(10).join(policy_lines)}
</traversal_policies>

<critical_rules>
- Location.prefecture_en format: 'Aichi Prefecture' (NOT 'Aichi' — always append ' Prefecture')
- ObservationTime.season values: 'Spring' | 'Summer' | 'Autumn' | 'Winter'
- ObservationTime.dayType values: 'Weekday' | 'Weekend'
- Station.stationtype_en values: 'General Station' | 'Roadside Station'
- ObservedPM25.pm25_level: 'Safe' | 'Moderate' | 'Slightly Unhealthy' | 'Unhealthy' | 'Very Unhealthy'
- Always add validity filter: WHERE p.pm25 >= 0 AND p.pm25 <= 500
- Do NOT use labels: Prefecture, Statistics, PM25Measurement, HAS_STATS, LOCATED_IN
</critical_rules>

<query>{nl_query}</query>

Cypher:"""
    return prompt


# ══════════════════════════════════════════════════════════════════════════════
# Main class
# ══════════════════════════════════════════════════════════════════════════════

class QueryGenerationSystems:
    """
    5 NL-to-Cypher generation systems for the Japan PM2.5 Knowledge Graph.
    Each method returns a standardized result dict.
    """

    # ── System 1: Baseline ─────────────────────────────────────────────────────

    def baseline(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        Zero-shot baseline: minimal prompt, no schema or domain knowledge.
        """
        prompt = (
            "Translate the following natural language query into a Cypher query "
            "for a Neo4j knowledge graph about PM2.5 air quality monitoring.\n\n"
            f"Query: {nl_query}\n\n"
            "Cypher:"
        )
        t0 = time.time()
        try:
            raw = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))

    # ── System 2: CypherBench-style ────────────────────────────────────────────

    def cypherbench_style(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        # Adapted from CypherBench (Feng et al., ACL 2025)
        Dynamically fetches schema from Neo4j. Provides full schema + strict
        instructions to use only defined labels/rel types.
        """
        t0 = time.time()
        try:
            schema_text = _fetch_neo4j_schema()
        except Exception as e:
            schema_text = f"[Schema fetch failed: {e}]"

        prompt = f"""You are a Cypher query expert for a Neo4j knowledge graph about PM2.5 air quality monitoring in Japan.

<schema>
{schema_text}
</schema>

STRICT RULES:
1. Only use node labels and relationship types listed in the schema above.
2. Do NOT invent labels or relationship types not in the schema.
3. Match property names exactly as they appear in the schema.
4. For aggregate queries, always use WITH before RETURN.
5. Add LIMIT to prevent full scans on large result sets.

Translate the following natural language query into a valid Cypher query.

Query: {nl_query}

Cypher:"""

        try:
            raw    = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))

    # ── System 3: Text2Cypher fine-tuned ──────────────────────────────────────

    def text2cypher_finetuned(self, nl_query: str) -> Dict[str, Any]:
        """
        Uses neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1 via HuggingFace.
        Falls back gracefully if model unavailable.
        """
        t0 = time.time()

        try:
            from pipeline.sota_ft_model import (
                is_available,
                get_load_error,
                generate_cypher as ft_generate,
                get_model_and_tokenizer,
            )
        except ImportError:
            # Try relative import
            try:
                from sota_ft_model import (
                    is_available,
                    get_load_error,
                    generate_cypher as ft_generate,
                )
            except ImportError:
                elapsed = (time.time() - t0) * 1000
                return _result(
                    None, elapsed, "",
                    error="model_unavailable: sota_ft_model not importable",
                )

        if not is_available():
            err = get_load_error() or "model_unavailable"
            elapsed = (time.time() - t0) * 1000
            return _result(None, elapsed, "", error=err)

        # Build schema text for the model card prompt format
        dkb    = _load_dkb()
        actual = dkb.get("kg_actual_schema", {})
        schema_lines = []
        for lbl in actual.get("node_labels", {}):
            props = actual.get("property_keys", {}).get(lbl, [])
            schema_lines.append(f"Node: {lbl} | Properties: {', '.join(props)}")
        for rt, info in actual.get("relationship_types", {}).items():
            schema_lines.append(f"Relationship: {info.get('pattern', rt)}")
        schema_text = "\n".join(schema_lines)

        # Build prompt (model card format)
        prompt = (
            f"<schema>\n{schema_text}\n</schema>\n\n"
            f"Translate the following question into a Cypher query for Neo4j.\n"
            f"Question: {nl_query}\n"
            f"Answer:"
        )

        try:
            cypher = ft_generate(nl_query, schema_text)
            # Strip markdown fences from output
            if cypher:
                cypher = re.sub(r"```(?:cypher)?\s*", "", cypher, flags=re.IGNORECASE)
                cypher = re.sub(r"```", "", cypher).strip() or None
            elapsed = (time.time() - t0) * 1000
            return _result(cypher, elapsed, prompt)
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            return _result(None, elapsed, prompt, error=str(e))

    # ── System 4: DKB ─────────────────────────────────────────────────────────

    def dkb(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        DKB-grounded prompt: schema_specification, pm25_health_rules,
        temporal_rules, traversal_policies, query_patterns from DKB.
        """
        t0 = time.time()
        prompt = _build_dkb_prompt_core(nl_query, extra_examples=None)
        try:
            raw    = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))

    # ── System 5: DKB-Hybrid ──────────────────────────────────────────────────

    # ── Ablation A: Schema + Values (Baseline C) ───────────────────────────────

    def schema_plus_values(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        Ablation: dynamic Neo4j schema + exact categorical values + critical
        formatting rules. No DKB examples, no health rules, no temporal rules,
        no traversal policies, no retrieval.

        This isolates the value-grounding contribution from the example/rule
        contribution. If SE >> cypherbench_style, value grounding is the key driver.
        """
        t0 = time.time()
        try:
            schema_text = _fetch_neo4j_schema()
        except Exception as e:
            schema_text = f"[Schema fetch failed: {e}]"

        # Enum values block — copied from DKB's kg_actual_schema.enum_values
        dkb    = _load_dkb()
        actual = dkb.get("kg_actual_schema", {})
        enum_vals = actual.get("enum_values", {})
        enum_lines = [f"  {k}: {v}" for k, v in enum_vals.items()]

        prompt = f"""You are a Cypher query expert for a Neo4j knowledge graph about PM2.5 air quality monitoring in Japan.

<schema>
{schema_text}
</schema>

<enum_values>
Exact categorical values — use PRECISELY as shown, character-for-character:
{chr(10).join(enum_lines)}
</enum_values>

<critical_rules>
- Location.prefecture_en format: 'Aichi Prefecture' (always append ' Prefecture' — NEVER write just 'Aichi')
- ObservationTime.season: 'Spring' | 'Summer' | 'Autumn' | 'Winter'
- ObservationTime.dayType: 'Weekday' | 'Weekend'
- Station.stationtype_en: 'General Station' | 'Roadside Station'
- ObservedPM25.pm25_level: 'Safe' | 'Moderate' | 'Slightly Unhealthy' | 'Unhealthy' | 'Very Unhealthy'
- Always add validity filter: WHERE p.pm25 >= 0 AND p.pm25 <= 500
- prefecture_en lives on Location, NOT on Station
- Do NOT use labels: Prefecture, Statistics, PM25Measurement, HAS_STATS, LOCATED_IN
</critical_rules>

STRICT RULES:
1. Only use node labels and relationship types listed in the schema above.
2. Use enum values EXACTLY as shown in <enum_values>.
3. For aggregate queries, always use WITH before RETURN.
4. Add LIMIT to prevent full scans on large result sets.

Translate the following natural language query into a valid Cypher query.

Query: {nl_query}

Cypher:"""

        try:
            raw    = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))

    # ── Ablation B: DKB without examples (Baseline E) ─────────────────────────

    def dkb_no_examples(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        Ablation: full DKB prompt (schema, enum values, health rules, temporal
        rules, traversal policies) with query_patterns section removed entirely.
        No hardcoded Cypher examples, no retrieved examples.

        The delta DKB - dkb_no_examples isolates the contribution of the 8
        hardcoded examples from the value/rule grounding contribution.
        """
        t0 = time.time()
        prompt = _build_dkb_prompt_no_examples(nl_query)
        try:
            raw    = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))

    def dkb_hybrid(self, nl_query: str, llm_name: str) -> Dict[str, Any]:
        """
        DKB + top-3 most similar examples via sentence-transformers all-MiniLM-L6-v2
        cosine similarity on nl_query vs pattern NL templates.
        """
        t0 = time.time()
        try:
            retrieved = _retrieve_top_k(nl_query, k=3)
        except Exception:
            retrieved = []

        prompt = _build_dkb_prompt_core(nl_query, extra_examples=retrieved)
        try:
            raw    = _call_ollama(llm_name, prompt)
            cypher = _extract_cypher(raw) or None
            return _result(cypher, (time.time() - t0) * 1000, prompt)
        except Exception as e:
            return _result(None, (time.time() - t0) * 1000, prompt, error=str(e))


# ── Quick smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    systems = QueryGenerationSystems()
    nl = "What is the average PM2.5 in Aichi Prefecture during winter?"
    llm = "qwen3.5:9b"

    for method_name in ["baseline", "cypherbench_style", "dkb", "dkb_hybrid"]:
        method = getattr(systems, method_name)
        print(f"\n{'='*60}")
        print(f"System: {method_name}")
        result = method(nl, llm)
        print(f"  Time: {result['generation_time_ms']:.0f}ms")
        print(f"  Error: {result['error']}")
        print(f"  Cypher:\n{result['generated_cypher']}")

    print(f"\n{'='*60}")
    print("System: text2cypher_finetuned")
    result = systems.text2cypher_finetuned(nl)
    print(f"  Time: {result['generation_time_ms']:.0f}ms")
    print(f"  Error: {result['error']}")
    print(f"  Cypher:\n{result['generated_cypher']}")
