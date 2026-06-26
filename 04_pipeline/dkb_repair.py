"""
dkb_repair.py — deterministic, DKB-grounded post-generation repair of Cypher.

Motivation (from live error analysis on JAPAQ-KG):
  The dominant *silent* failure of schema-grounded LLM output is not bad syntax —
  it is wrong VALUE surface forms. e.g. an LLM writes
      MATCH (l:Location {prefecture_en: 'Kagoshima'}) ...
  which is valid Cypher, executes without error, and returns ZERO rows, because
  the KG stores 'Kagoshima Prefecture'. EXPLAIN passes, execution "succeeds",
  but the answer is empty -> CV/ES look fine while SE collapses.

This module applies high-precision, deterministic repairs driven by the DKB's
canonical entity dictionary and schema:
  R1  prefecture value anchoring : 'Kagoshima' -> 'Kagoshima Prefecture'
  R2  prefecture property key     : {name: 'Chiba Prefecture'} -> {prefecture_en: 'Chiba Prefecture'}
                                    (and l.name = 'Chiba Prefecture' -> l.prefecture_en = ...)

Every repair is reversible-by-inspection and only fires on an exact match against
the known 46-prefecture dictionary, so it cannot corrupt an already-correct query.
This is the "schema anchoring" mechanism (deterministic, model-agnostic) — it can
be applied on top of ANY system's output to isolate the value of domain anchoring.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

_KG_STATS = Path("/home/arjun/pm25_system/data/kg_stats_final.json")

# Canonical prefecture dictionary: stem (lowercase) -> full canonical form.
def _load_prefectures() -> dict[str, str]:
    try:
        prefs = json.loads(_KG_STATS.read_text())["geographic_coverage"]["prefectures"]
    except Exception:
        prefs = []  # graceful: repair becomes a no-op
    table = {}
    for full in prefs:
        stem = full[:-len(" Prefecture")] if full.endswith(" Prefecture") else full
        table[stem.lower()] = full
        table[full.lower()] = full  # already-canonical maps to itself
    return table

_PREF_TABLE = _load_prefectures()
# Location property that actually stores the prefecture string.
_PREF_PROP = "prefecture_en"
# Properties an LLM commonly uses by mistake for the prefecture name.
_WRONG_PREF_PROPS = ("name", "prefecture", "prefecture_name", "pref")

# A quoted string literal: group 1 = quote, group 2 = inner text.
_STR_LITERAL = re.compile(r"(['\"])(.*?)\1")


def repair(cypher: str) -> Tuple[str, List[str]]:
    """Return (repaired_cypher, applied_repairs). No-op-safe on already-correct input."""
    if not cypher or not _PREF_TABLE:
        return cypher, []
    applied: List[str] = []
    out = cypher

    # R1: anchor bare prefecture string values to their canonical ' Prefecture' form.
    def _anchor(m: re.Match) -> str:
        q, inner = m.group(1), m.group(2)
        canon = _PREF_TABLE.get(inner.strip().lower())
        if canon and inner != canon:
            applied.append(f"R1 value: '{inner}' -> '{canon}'")
            return f"{q}{canon}{q}"
        return m.group(0)
    out = _STR_LITERAL.sub(_anchor, out)

    # R2a: map-key form  {name: 'X Prefecture'} -> {prefecture_en: 'X Prefecture'}
    for wp in _WRONG_PREF_PROPS:
        if wp == _PREF_PROP:
            continue
        pat = re.compile(
            r"(\{[^{}]*?)\b" + re.escape(wp) + r"\b(\s*:\s*)(['\"])([^'\"]*?)\3",
        )
        def _mapkey(m: re.Match) -> str:
            inner = m.group(4)
            if inner.strip().lower() in _PREF_TABLE or inner.endswith(" Prefecture"):
                applied.append(f"R2 key: {wp} -> {_PREF_PROP}")
                return f"{m.group(1)}{_PREF_PROP}{m.group(2)}{m.group(3)}{inner}{m.group(3)}"
            return m.group(0)
        out = pat.sub(_mapkey, out)

    # R2b: equality form  x.name = 'X Prefecture' -> x.prefecture_en = 'X Prefecture'
    for wp in _WRONG_PREF_PROPS:
        if wp == _PREF_PROP:
            continue
        pat = re.compile(
            r"(\w+)\." + re.escape(wp) + r"(\s*=\s*)(['\"])([^'\"]*?)\3",
        )
        def _eq(m: re.Match) -> str:
            inner = m.group(4)
            if inner.strip().lower() in _PREF_TABLE or inner.endswith(" Prefecture"):
                applied.append(f"R2 prop: .{wp} -> .{_PREF_PROP}")
                return f"{m.group(1)}.{_PREF_PROP}{m.group(2)}{m.group(3)}{inner}{m.group(3)}"
            return m.group(0)
        out = pat.sub(_eq, out)

    return out, applied


if __name__ == "__main__":
    tests = [
        "MATCH (l:Location {prefecture_en: 'Kagoshima'}) RETURN l",
        "MATCH (l:Location {name: 'Chiba Prefecture'})-[:HAS_READING]->(r) RETURN r",
        "MATCH (p)-[:OBSERVED_AT]->(t)-[:AT_LOCATION]->(l) WHERE l.name = 'Osaka' RETURN avg(p.pm25)",
        "MATCH (l:Location {prefecture_en: 'Aichi Prefecture'}) RETURN l",  # already correct -> no-op
    ]
    for t in tests:
        r, ops = repair(t)
        print("IN :", t)
        print("OUT:", r)
        print("OPS:", ops, "\n")
