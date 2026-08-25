"""
k_systems.py — non-destructive, k-parameterised copy of the published
DKB+Hybrid generation path.

Nothing here re-implements the prompt, the DKB, the embedding model, the
similarity metric or the Ollama call: every one of those is imported
unchanged from the historical pipeline/systems.py.  The ONLY thing this
wrapper changes is the hard-coded `k=3` at the single call site
(systems.py:784) and it records audit metadata.

Published mechanism preserved exactly:
    patterns_to_show = retrieved + query_patterns[:8]   then truncated to [:8]
=> k=1 -> 1 retrieved + JP01..JP07, k=3 -> 3 + JP01..JP05, k=5 -> 5 + JP01..JP03.
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path
from typing import Any, Dict

# systems.py sets these itself, but set them here too so the sentence-transformers
# import cannot fall back to the Keras-3 failure path (which would silently give
# zero retrieved exemplars).
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5]))
sys.path.insert(0, str(ROOT))

from pipeline.systems import (           # READ-ONLY reuse of the published code
    _retrieve_top_k,
    _build_dkb_prompt_core,
    _call_ollama,
    _extract_cypher,
)

DEFAULT_K = 3          # preserves the submitted system's behaviour


def retrieve(nl_query: str, k: int = DEFAULT_K) -> list[dict]:
    """Strict retrieval: NO silent fallback to []. Raises if retrieval fails."""
    out = _retrieve_top_k(nl_query, k=k)
    if len(out) != k:
        raise RuntimeError(f"retrieval returned {len(out)} exemplars, expected {k}")
    return out


def build_prompt(nl_query: str, k: int = DEFAULT_K) -> tuple[str, list[str]]:
    retrieved = retrieve(nl_query, k=k)
    prompt = _build_dkb_prompt_core(nl_query, extra_examples=retrieved)
    return prompt, [p["pattern_id"] for p in retrieved]


def dkb_hybrid_k(nl_query: str, llm_name: str, k: int = DEFAULT_K) -> Dict[str, Any]:
    """Same control flow as systems.dkb_hybrid, with k parameterised and the
    retrieval fallback removed (a retrieval failure must abort, not degrade)."""
    t0 = time.time()
    prompt, ids = build_prompt(nl_query, k=k)
    try:
        raw = _call_ollama(llm_name, prompt)
        cypher = _extract_cypher(raw) or None
        err = None
    except Exception as e:
        cypher, err = None, str(e)
    return {
        "generated_cypher": cypher,
        "generation_time_ms": (time.time() - t0) * 1000,
        "error": err,
        "prompt_used": prompt,
        "retrieval_k": k,
        "retrieved_exemplar_ids": ids,
    }
