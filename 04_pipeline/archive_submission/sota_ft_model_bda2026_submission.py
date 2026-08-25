"""
sota_ft_model.py — Loader for Neo4j text2cypher fine-tuned models via HuggingFace.

Supports multiple models selectable via FT_MODEL_NAME env var:
  - gemma2-9b  → neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1  (default)
  - llama3-8b  → neo4j/text2cypher-llama3-8b-instruct-finetuned-2024v1
  - qwen2.5-7b → neo4j/text2cypher-qwen2.5-7b-instruct-finetuned-2024v1

All models share the same prompt format and generation logic.
Returns None gracefully if model/libraries unavailable.
"""

from __future__ import annotations
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL_REGISTRY = {
    "gemma2-9b":  "neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1",
    "llama3-8b":  "neo4j/text2cypher-llama3-8b-instruct-finetuned-2024v1",
    "qwen2.5-7b": "neo4j/text2cypher-qwen2.5-7b-instruct-finetuned-2024v1",
}

_DEFAULT_MODEL = "gemma2-9b"

def _active_model_id() -> str:
    key = os.environ.get("FT_MODEL_NAME", _DEFAULT_MODEL)
    return _MODEL_REGISTRY.get(key, _MODEL_REGISTRY[_DEFAULT_MODEL])

# Model ID exposed for external reference
MODEL_ID = _active_model_id()

# Per-model cache keyed by HF model ID
_cache: dict[str, dict] = {}


def _get_cache(model_id: str) -> dict:
    if model_id not in _cache:
        _cache[model_id] = {"model": None, "tokenizer": None, "loaded": False, "error": None}
    return _cache[model_id]


def _try_load(model_id: str):
    c = _get_cache(model_id)
    if c["loaded"]:
        return

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        hf_token = os.getenv("HF_TOKEN")
        logger.info(f"Loading {model_id} with 4-bit quantization...")
        c["tokenizer"] = AutoTokenizer.from_pretrained(model_id, token=hf_token)
        c["model"] = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            token=hf_token,
        )
        c["model"].eval()
        c["loaded"] = True
        logger.info(f"Loaded {model_id} successfully.")

    except ImportError as e:
        c["error"] = f"Missing library: {e}. Install transformers, bitsandbytes, torch."
        c["loaded"] = True
        logger.warning(c["error"])
    except OSError as e:
        c["error"] = f"Model not found or download failed: {e}"
        c["loaded"] = True
        logger.warning(c["error"])
    except Exception as e:
        c["error"] = f"Unexpected error loading model: {e}"
        c["loaded"] = True
        logger.warning(c["error"])


def get_model_and_tokenizer(model_id: str | None = None):
    mid = model_id or _active_model_id()
    _try_load(mid)
    c = _get_cache(mid)
    if c["error"]:
        return None, None
    return c["model"], c["tokenizer"]


def is_available(model_id: str | None = None) -> bool:
    mid = model_id or _active_model_id()
    _try_load(mid)
    c = _get_cache(mid)
    return c["model"] is not None and c["tokenizer"] is not None


def get_load_error(model_id: str | None = None) -> Optional[str]:
    mid = model_id or _active_model_id()
    _try_load(mid)
    return _get_cache(mid)["error"]


def generate_cypher(
    nl_query: str,
    schema_text: str,
    max_new_tokens: int = 256,
    model_id: str | None = None,
) -> Optional[str]:
    """
    Generate Cypher using the Neo4j text2cypher prompt format:
      <schema>...</schema>
      Question: ...
      Answer:
    """
    mid = model_id or _active_model_id()
    model, tokenizer = get_model_and_tokenizer(mid)
    if model is None or tokenizer is None:
        return None

    try:
        import torch

        prompt = (
            f"<schema>\n{schema_text}\n</schema>\n\n"
            f"Translate the following question into a Cypher query for Neo4j.\n"
            f"Question: {nl_query}\n"
            f"Answer:"
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        generated = re.sub(r"```(?:cypher)?\s*", "", generated, flags=re.IGNORECASE)
        generated = re.sub(r"```", "", generated)

        lines = generated.strip().splitlines()
        start = 0
        for i, line in enumerate(lines):
            if re.match(r"^\s*(MATCH|WITH|CALL|RETURN|MERGE|CREATE|OPTIONAL)", line, re.IGNORECASE):
                start = i
                break
        return "\n".join(lines[start:]).strip() or None

    except Exception as e:
        logger.error(f"Generation error: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for key, mid in _MODEL_REGISTRY.items():
        print(f"\n--- {key}: {mid} ---")
        if is_available(mid):
            result = generate_cypher(
                "What is the average PM2.5 in Tokyo Prefecture?",
                "Node: ObservedPM25 | Properties: pm25\nNode: Location | Properties: prefecture_en",
                model_id=mid,
            )
            print(f"Generated: {result}")
        else:
            print(f"Unavailable: {get_load_error(mid)}")
