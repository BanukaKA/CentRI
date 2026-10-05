# CentRI

**Central Routing Intelligence** — a semantic API gateway for agent swarms. Offline compilation expands each agent into a cluster of synthetic utterances; runtime routing is **retrieve (FAISS + k-NN vote) → re-rank (micro-LLM on Top-K schemas)** with optional **multi-intent sharding** and a **feedback loop** that appends correction vectors.

Built for [Nebius Token Factory](https://docs.tokenfactory.nebius.com/) (OpenAI-compatible embeddings + chat) and optional [Tavily](https://tavily.com/) grounding for time-sensitive synthetic query generation.

## What CentRI solves

Large organizations increasingly expose many specialized agents: IT support,
finance controls, HR policy, legal review, sales research, customer care,
engineering incident response, compliance, product, and marketing. The user
still needs one entry point, but asking a large LLM to inspect every agent
schema on every request creates a growing prompt, rising token cost, more
latency, and more semantic collisions between adjacent agents.

CentRI is the routing control plane between the user and that agent catalog:

```text
User request
    -> CentRI gateway
    -> one or more selected agent IDs
    -> configured agent runtime(s)
    -> response or compound synthesis
```

Its business use case is an enterprise agent platform where teams can add or
update agents without rewriting a monolithic router prompt or retraining a
closed classifier for every catalog change. The initial sample catalog models
Northstar Services Group and contains 10 enterprise agents; the architecture
is designed for a much larger catalog.

## The true innovation

CentRI's core innovation is **compiled semantic routing memory plus bounded
runtime disambiguation**:

1. **Compile at change time.** Agent schemas are expanded into diverse
   synthetic user utterances, including contrastive examples against adjacent
   agents. The utterances are embedded once and stored as searchable routing
   memory.
2. **Retrieve at request time.** The user query is embedded and FAISS retrieves
   a small high-recall candidate set rather than sending the entire catalog to
   a generative model.
3. **Reason only over ambiguity.** A micro-LLM sees the query and only the
   Top-K candidate routing cards. It resolves collisions such as payroll vs.
   HR policy or employee support vs. engineering incidents.
4. **Learn from routing outcomes.** Redacted shadow telemetry and reviewed
   corrections add evidence to the routing surface without retraining the
   whole agent system.

This is not a claim that vector search is automatically more accurate than
every classifier or LLM. Retrieval recall, reranker quality, abstention,
catalog quality, and latency must be measured. The architectural advantage is
that the request-time reasoning surface is bounded by `K`, while the catalog
can grow independently.

## Full technical span

### Offline compilation plane

`sample_agent_router_dataset.json` is parsed into an agent registry. For each
agent, CentRI uses routing examples, golden cases, keywords, descriptions,
tools, exclusions, required entities, workflow metadata, and adjacent-agent
cards to build a query bank. Nebius generates additional synthetic queries
when `--synthesize` is enabled. Tavily is optionally used only for fresh web
context while generating examples for time-sensitive domains.

Nebius then embeds the query bank with `Qwen/Qwen3-Embedding-8B`. Vectors are
normalized and written to a configurable FAISS index:

- `hnsw`: scalable approximate nearest-neighbor search for runtime
- `flat`: exact `IndexFlatIP` baseline for evaluation

Compiled artifacts are:

```text
data/compiled/faiss.index
data/compiled/vectors.jsonl
data/compiled/index_meta.json
data/compiled/manifest.json
data/compiled/synthetic_queries.json
```

The manifest fingerprints the catalog and embedding model so a stale index is
rejected when the source catalog or embedding configuration changes.

### Runtime routing plane

`POST /route` and `POST /chat` use this cascade:

```text
request validation
    -> optional JWT authentication
    -> intent splitting and shard cap
    -> query embedding
    -> FAISS Top-K retrieval
    -> per-agent score aggregation
    -> catalog exclusion policy
    -> Top-3 routing-card reranking
    -> similarity / margin / confidence abstention
    -> agent ID decision
```

The current aggregation score is:

```text
agent_score = max(vector_similarity) + 0.02 * hit_count
```

`/route` returns routing decisions only. `/chat` concurrently dispatches
independent shards to configured HTTP runtimes, applies human-approval gates
for agents with side-effect metadata, and optionally asks Nebius to synthesize
multiple successful results.

### Execution and orchestration plane

The generic adapter in `centri/agents/executor.py` supports:

- endpoint URLs in an agent's `runtime.endpoint_url`
- endpoint mappings in `CENTRI_AGENT_ENDPOINTS_JSON`
- async HTTP handoff with timeout handling
- workflow dependency ordering
- human-review and write-tool approval gates
- explicit simulated fallback for the sample catalog

No live agent services are included in the repository, so the sample catalog
uses simulation until an endpoint is configured.

### Learning and governance plane

CentRI writes request IDs, latency, routing outcome, status, and hashed prompt
identifiers to shadow logs. Raw prompts and queries are redacted by default.
Corrections are validated against known agent IDs, deduplicated, versioned, and
written through atomic index replacement. JWT bearer authentication protects
non-health endpoints when enabled; feedback requires `admin` or `operator`.

### Core terminology

- **Embedding:** numerical vector representation of text used for semantic
  similarity.
- **Dense retrieval:** nearest-neighbor search over learned vectors.
- **ANN:** approximate nearest-neighbor search; faster at scale with a recall
  trade-off.
- **HNSW:** graph-based ANN index used as the default production-oriented
  index.
- **Flat / IndexFlatIP:** exact exhaustive inner-product search used as the
  evaluation baseline.
- **Retrieve-and-rerank:** high-recall candidate retrieval followed by a
  higher-precision model over a small candidate set.
- **Routing card:** compact agent schema shown to the reranker instead of the
  agent's complete system prompt.
- **Abstention:** refusing to guess when similarity, candidate margin, or
  reranker confidence is below policy.
- **Compound intent:** one user request split into multiple independently
  routable shards.
- **Shadow telemetry:** routing observations recorded for evaluation and
  correction without changing the user response.

## Architecture artifact

Open [`docs/centri-architecture.excalidraw`](docs/centri-architecture.excalidraw) in Excalidraw for the full architecture, scaling model, comparison with prompt-all LLM routing, typed one-pass decision models such as Jev, production boundary, and research sources. Regenerate it with:

```bash
python scripts/generate_architecture_diagram.py
```

The five-minute technical presentation is available at
[`CentRI_5_minute_presentation.pptx`](CentRI_5_minute_presentation.pptx). Regenerate it with:

```bash
python scripts/generate_presentation.py
```

## Architecture

| Phase | What runs | Output |
|--------|-----------|--------|
| **Compile** (on catalog change) | Seed + contrastive synthetic queries, Nebius embeddings | `data/compiled/faiss.index` + `vectors.jsonl` |
| **Gateway** (per request) | Intent split → embed → Top-K vector vote → LLM re-rank → agent handoff | `/chat` JSON |
| **Learn** (continuous) | Shadow logs + `/feedback/routing` + `scripts/correct_routing.py` | New vectors in index |

Agent catalog: `sample_agent_router_dataset.json` (10 Northstar enterprise agents).

## Quick start

The following is the complete Windows PowerShell flow from a clean checkout.

### 1. Create and activate the environment

```bash
cd "C:\Users\Banuka Ambegoda\Documents\GitHub\CentRI"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

If PowerShell blocks activation, run the project commands directly through
`.venv\Scripts\python.exe` instead.

### 2. Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `NEBIUS_API_KEY`. `TAVILY_API_KEY` is optional and is used by
`--synthesize`. Local development can use:

```dotenv
CENTRI_AUTH_REQUIRED=false
CENTRI_MOCK_EXECUTION=true
```

For a protected deployment, set `CENTRI_AUTH_REQUIRED=true` and a strong
`CENTRI_JWT_SECRET`. Do not commit `.env` or expose its keys.

### 3. Compile the routing index

The default compile uses catalog examples and golden cases:

```powershell
python -m scripts.compile
```

For full contrastive synthetic expansion, run:

```powershell
python -m scripts.compile --synthesize --force-synthesize
```

This creates the FAISS index and manifest under `data/compiled/`. Recompile
whenever the catalog, embedding model, index type, or synthesis configuration
changes.

### 4. Validate the catalog and routing

Catalog-only validation needs no network calls:

```powershell
python -m scripts.evaluate_routing --catalog-only
```

Full golden-case evaluation uses Nebius and the compiled index:

```powershell
python -m scripts.evaluate_routing --output data/routing_eval.json
```

### 5. Start the gateway

```powershell
python -m centri.gateway.app
```

The service listens on `http://localhost:8080`. Interactive API documentation
is available at `http://localhost:8080/docs`.

### 6. Smoke-test the running system

Health:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

Route only:

```powershell
$body = @{ query = "My VPN broke after a password reset." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/route `
  -Method Post -ContentType "application/json" -Body $body
```

Route and execute:

```powershell
$body = @{
  prompt = "My VPN broke after a password reset."
  approval_granted = $true
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/chat `
  -Method Post -ContentType "application/json" -Body $body
```

All Postman-ready cURL examples are in [`postman_test.txt`](postman_test.txt).

Compound requests may return multiple `results[]` entries and a synthesized
response:

```powershell
$body = @{ query = "Analyze cloud spend and prepare an incident summary." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/route `
  -Method Post -ContentType "application/json" -Body $body
```

## Configuration

See `.env.example`. Key settings:

- `CENTRI_EMBEDDING_MODEL` — default `Qwen/Qwen3-Embedding-8B` ([Nebius embeddings](https://docs.tokenfactory.nebius.com/api-reference/examples/create-embeddings))
- `CENTRI_LLM_MODEL` — stage-2 re-rank + intent splitter (small, low latency)
- `CENTRI_LLM_MODEL_SYNTHESIS` — offline query generation + nightly correction
- `CENTRI_INDEX_TYPE` — `hnsw` for scalable approximate search or `flat` for the exact baseline
- `CENTRI_ROUTE_MIN_SIMILARITY` / `CENTRI_ROUTE_MIN_MARGIN` — abstention controls
- `CENTRI_RUNTIME_TIMEOUT_SECONDS` — HTTP agent handoff timeout
- `CENTRI_REDACT_TELEMETRY` / `CENTRI_LOG_RETENTION_DAYS` — safe shadow-log controls

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/catalog` | All agents: `agent_id`, `name`, optional `display_name`, `description` |
| `GET` | `/agents` | Same catalog fields plus `domain` |
| `POST` | `/route` | Route a `query` → `agent_id` and `agent_name` (no agent execution) |
| `POST` | `/chat` | Route + concurrent agent execution + compound synthesis |
| `POST` | `/feedback/routing` | Log refusal or append correction vector |

`/route` and `/chat` can abstain when similarity, candidate margin, or reranker
confidence is below policy thresholds. `/chat` accepts `approval_granted` for
catalog-declared side-effect/human-review gates.

### HTTP agent runtime contract

When an endpoint is configured, CentRI sends a JSON `POST` payload like:

```json
{
  "agent_id": "agt_it_service_desk_triage",
  "agent_name": "IT Service Desk Triage Agent",
  "prompt": "My VPN stopped after a password change.",
  "intent_shard": "troubleshoot VPN connection issue",
  "history": [],
  "routing": {
    "confidence": 0.95,
    "rationale": "..."
  },
  "workflow": [],
  "guardrails": {}
}
```

The runtime may return JSON or plain text. CentRI applies its timeout,
approval, and failure handling around that call. It does not invent a live
endpoint for the sample catalog; without one, `CENTRI_MOCK_EXECUTION=true`
returns a clearly marked `simulated` response.

## What is implemented versus external

Implemented in this repository:

- catalog registry and schema-derived routing cards
- Nebius embeddings, intent splitting, reranking, and synthesis
- Tavily-assisted offline query generation
- HNSW/Flat FAISS indexing with manifests and atomic writes
- multi-intent routing and concurrent handoff orchestration
- abstention, exclusions, approval gates, JWT protection, and redacted logs
- golden-case evaluation and operational documentation

External or deployment-specific:

- actual specialized agent services and their tools
- production identity provider and JWT issuance
- distributed vector storage and multi-process index coordination
- durable workflow state, tracing backend, and metrics backend
- business-specific authorization and data-residency policy

## Evaluation

Validate the catalog without external services:

```bash
python -m scripts.evaluate_routing --catalog-only
```

Run the full Nebius-backed golden-case evaluation after compiling:

```bash
python -m scripts.evaluate_routing --output data/routing_eval.json
```

The report includes top-1 accuracy, candidate recall, abstention rate,
confusion pairs, mean latency, and p95 latency.

## Project layout

```
centri/
  clients/       # Nebius + Tavily
  synthesis/     # Contrastive query expansion
  index/         # FAISS store
  routing/       # Intent split, vote, re-rank
  gateway/       # FastAPI
  agents/        # HTTP executor, workflow ordering, mock fallback
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
