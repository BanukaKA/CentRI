# CentRI

**Central Routing Intelligence** — a semantic API gateway for agent swarms. Offline compilation expands each agent into a cluster of synthetic utterances; runtime routing is **retrieve (FAISS + k-NN vote) → re-rank (micro-LLM on Top-K schemas)** with optional **multi-intent sharding** and a **feedback loop** that appends correction vectors.

Built for [Nebius Token Factory](https://docs.tokenfactory.nebius.com/) (OpenAI-compatible embeddings + chat) and optional [Tavily](https://tavily.com/) grounding for time-sensitive synthetic query generation.

## Architecture

| Phase | What runs | Output |
|--------|-----------|--------|
| **Compile** (on catalog change) | Seed + contrastive synthetic queries, Nebius embeddings | `data/compiled/faiss.index` + `vectors.jsonl` |
| **Gateway** (per request) | Intent split → embed → Top-K vector vote → LLM re-rank → agent handoff | `/chat` JSON |
| **Learn** (continuous) | Shadow logs + `/feedback/routing` + `scripts/correct_routing.py` | New vectors in index |

Agent catalog: `sample_agent_router_dataset.json` (10 Northstar enterprise agents).

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"

copy .env.example .env
# Set NEBIUS_API_KEY (required). TAVILY_API_KEY optional.

# Offline compile (seeds only — fast PoC)
python -m scripts.compile

# Full contrastive synthetic expansion (~50 queries/agent, uses synthesis LLM + Tavily when freshness SLA ≤ 30d)
python -m scripts.compile --synthesize

# Gateway
python -m centri.gateway.app
# or: uvicorn centri.gateway.app:app --host 0.0.0.0 --port 8080
```

### Example request

```bash
curl -s http://localhost:8080/chat -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"My VPN broke after a password reset and I need a ticket.\"}"
```

Compound intents return multiple `results[]` entries (e.g. FinOps + calendar-style prompts).

## Configuration

See `.env.example`. Key settings:

- `CENTRI_EMBEDDING_MODEL` — default `BAAI/bge-en-icl` ([Nebius embeddings](https://docs.tokenfactory.nebius.com/api-reference/examples/create-embeddings))
- `CENTRI_LLM_MODEL` — stage-2 re-rank + intent splitter (small, low latency)
- `CENTRI_LLM_MODEL_SYNTHESIS` — offline query generation + nightly correction

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/agents` | Catalog summary |
| `POST` | `/chat` | Route + stub agent execution |
| `POST` | `/feedback/routing` | Log refusal or append correction vector |

## Project layout

```
centri/
  clients/       # Nebius + Tavily
  synthesis/     # Contrastive query expansion
  index/         # FAISS store
  routing/       # Intent split, vote, re-rank
  gateway/       # FastAPI
  agents/        # Stub executor (swap for real endpoints)
  feedback/      # Shadow logging
scripts/
  compile.py
  correct_routing.py
```

## Tests

```bash
pytest
```

## License

See [LICENSE](LICENSE).
