# Three-minute CentRI demo script

This is the recommended screen-recording sequence for the Nebius x NVIDIA
Global AI Hackathon submission.

## 0:00–0:20 — The problem

Say:

> Enterprise agent catalogs grow faster than a single router prompt can stay
> accurate. CentRI is the semantic API gateway that gives the catalog one
> front door.

Show the architecture diagram:

```text
docs/centri-architecture.excalidraw
```

## 0:20–0:45 — Open infrastructure

Show `.env` with secrets hidden and point out:

```text
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
CENTRI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
CENTRI_LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
```

Say:

> Embeddings create the routing memory. NVIDIA Nemotron on Nebius performs
> runtime intent splitting and precision reranking.

## 0:45–1:10 — Compile the catalog

Run:

```powershell
python -m scripts.compile
```

Show:

```text
data/compiled/faiss.index
data/compiled/index_meta.json
data/compiled/manifest.json
data/compiled/vectors.jsonl
```

Say:

> Compilation happens when agents change, not when every user asks a
> question. This is the amortization step.

## 1:10–1:50 — Route one request

Start the gateway:

```powershell
python -m centri.gateway.app
```

Open `http://localhost:8080/docs`, call `POST /route`, and use:

```json
{
  "query": "My VPN stopped after a password change."
}
```

Point out:

- selected `agent_id`
- selected `agent_name`
- Top-3 candidates
- similarity
- candidate margin
- Nemotron rationale

Say:

> Retrieval narrows the entire catalog to a few candidates. Nemotron only
> resolves the ambiguity among those candidates.

## 1:50–2:20 — Compound intent

Call `POST /route` with:

```json
{
  "query": "Analyze cloud infrastructure spend and prepare an incident summary."
}
```

Show the multiple `routes[]` entries.

Say:

> A compound request becomes independently routable shards. `/chat` can
> execute those shards concurrently and synthesize successful results.

## 2:20–2:40 — Governance and safety

Show:

- abstention fields
- `approval_granted`
- JWT configuration
- redacted shadow logs

Say:

> CentRI does not force a guess. It can abstain when evidence is weak and
> requires approval before catalog-declared side effects.

## 2:40–3:00 — Evidence

Run:

```powershell
python -m scripts.benchmark_router --output data/benchmark_report.json
```

Show [`docs/benchmark_report.md`](benchmark_report.md).

Close with:

> On the current 20-case synthetic benchmark, CentRI retrieved the correct
> candidate for every case and achieved 100% selective accuracy at 80%
> coverage. The next scale test is a larger human-authored catalog and live
> agent runtimes.

