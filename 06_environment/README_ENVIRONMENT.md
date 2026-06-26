# Software Environment

## Hardware Used

| Component | Specification |
|---|---|
| GPU | 2× NVIDIA RTX A6000 (48 GB VRAM each, 96 GB total) |
| RAM | 128 GB |
| Storage | NVMe SSD, 2 TB |
| OS | Ubuntu 22.04 LTS |

## Minimum Requirements for Reproduction

| Component | Minimum |
|---|---|
| GPU VRAM | 48 GB (for qwen2.5:72b via Ollama) |
| System RAM | 64 GB |
| Disk | 300 GB (Neo4j data) + 100 GB (LLM models) |

## Software Versions

| Software | Version | Purpose |
|---|---|---|
| Python | 3.12.4 | Pipeline runtime |
| CUDA | 12.x | GPU inference |
| Docker | 24.x | Neo4j container |
| Neo4j | 2026.02.2 | Knowledge graph |
| Ollama | Latest | LLM inference server |

## Python Packages

See `requirements.txt` for full pinned versions. Key packages:

| Package | Version | Purpose |
|---|---|---|
| neo4j | 6.0.2 | Neo4j Python driver |
| sentence-transformers | 5.1.1 | Embedding-based retrieval |
| rank-bm25 | 0.2.2 | BM25 keyword retrieval |
| scipy | 1.15.3 | Statistical tests |
| numpy | 1.26.4 | Numerical computing |
| pandas | 2.2.2 | Table generation |
| matplotlib | 3.9.2 | Figure generation |
| transformers | 4.56.1 | text2cypher fine-tuned model |
| torch | 2.7.1 | GPU inference |

## Install

```bash
pip install -r requirements.txt
```

## Files

| File | Description |
|---|---|
| `requirements.txt` | Pinned Python package versions |
| `ollama_models.txt` | LLM pull commands for Ollama |
| `docker_setup.md` | Neo4j Docker configuration details |
