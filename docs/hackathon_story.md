# CentRI System Story

## Inspiration

As an Applied AI Engineer working on systems that operate at global scale, I have seen that coordination - not model intelligence alone - becomes the bottleneck as services, capabilities, and possible destinations multiply. Agent networks create the same problem: users need one simple entry point, while an enterprise may eventually operate thousands, tens of thousands, or millions of specialized agents.

I wanted to explore an independent architecture focused on **speed and accuracy as well as scale**. CentRI is my own implementation, built from a public synthetic agent registry for this hackathon. Its central idea is to compile agent capabilities into semantic routing memory, retrieve only the relevant candidates, and use model reasoning only for the remaining ambiguity.

## What it does

CentRI is a semantic API gateway and routing control plane for enterprise agent networks. It turns a large agent catalog into one stable interface:

```text
user request -> CentRI -> agent_id -> authorized agent runtime
```

CentRI:

- Accepts requests through a unified FastAPI gateway.
- Detects and shards compound intent.
- Searches compiled capability memory with local HNSW/FAISS retrieval.
- Aggregates evidence across multiple examples belonging to each agent.
- Uses NVIDIA Nemotron through Nebius Token Factory to rerank only the highest-value candidates.
- Returns the agent ID, name, confidence, rationale, and candidate evidence.
- Abstains instead of forcing a low-confidence handoff.
- Executes independent shards concurrently through HTTP agent adapters.
- Enforces JWT roles, approval gates, workflow ordering, and redacted telemetry.

This allows an enterprise to share approved agents, proprietary data access, tools, workflows, and organizational expertise efficiently with authorized users without placing the entire agent catalog into every prompt.

## How we built it

CentRI is organized into an offline compilation plane, a runtime routing plane, and a learning/governance plane.

### Offline compilation

When an agent is added or updated, CentRI reads its schema from the registry: description, domain, tools, example queries, exclusions, required entities, workflow metadata, guardrails, and evaluation cases.

It then:

1. Generates diverse synthetic user utterances.
2. Generates contrastive examples against adjacent agents to sharpen semantic boundaries.
3. Embeds the query bank using `Qwen/Qwen3-Embedding-8B`.
4. Normalizes the vectors for cosine-style similarity.
5. Builds either an exact Flat FAISS baseline or an HNSW approximate-nearest-neighbor index.
6. Writes versioned metadata and a catalog/model fingerprint.

Tavily can provide current web context during offline generation and can be
invoked on the live `/chat` path with `use_web_search: true` for
freshness-sensitive requests. The returned research context is passed into
the selected agent handoff.

### Runtime routing

For each request, CentRI performs:

```text
request validation
  -> intent sharding
  -> embedding
  -> local HNSW retrieval
  -> agent score aggregation
  -> policy filtering
  -> Top-K routing cards
  -> NVIDIA Nemotron reranking
  -> confidence/margin abstention
  -> agent ID handoff
```

Let \(A\) be the number of agents, \(S\) the average schema size, \(K\) the reranking candidate count, and \(R\) the compact routing-card size. A prompt-all router exposes approximately:

\[
C_{\mathrm{prompt\text{-}all}} \approx A \times S
\]

CentRI instead exposes the model to approximately:

\[
C_{\mathrm{CentRI}} \approx Q + K \times R,\qquad K \ll A
\]

where \(Q\) is the user request context. The catalog can grow while the reasoning context remains bounded.

The routing memory and vector search run locally in the CentRI control plane. NVIDIA Nemotron runs on GPU infrastructure through Nebius Token Factory, but receives only the bounded candidate context. This separates local discovery from GPU-backed disambiguation.

### Execution and governance

The selected agent can be reached through a configured asynchronous HTTP runtime. For compound requests, independent shards are executed concurrently and successful results can be synthesized. The platform also includes:

- JWT authentication and operator/admin roles
- human-approval gates for side-effecting tools
- workflow dependency ordering
- explicit mock fallback for the sample catalog
- redacted shadow telemetry
- correction vectors and atomic index updates
- golden-case evaluation and benchmark reporting

## Challenges we ran into

### Semantic collisions

Agents often share vocabulary. HR, payroll, finance, support, and engineering agents can all mention employees, access, incidents, or accounts. Keyword matching alone is not enough.

CentRI addresses this with contrastive synthetic examples, dense retrieval, compact routing cards, catalog exclusions, score margins, and a second-stage Nemotron decision.

### Compound intent

Real users combine tasks in one request. A single prompt may require several agents and may contain dependencies between them. CentRI bounds the number of shards, routes them independently, and executes independent work concurrently.

### Accuracy versus forced coverage

A router that always selects an agent can hide uncertainty and create unsafe handoffs. CentRI treats abstention as a first-class outcome. If the similarity, candidate margin, or reranker confidence is insufficient, it returns an abstention rather than inventing certainty.

### Local routing versus GPU inference

The system needed the quality of a capable decision model without repeatedly sending the full enterprise catalog to GPU inference. Keeping compiled memory and HNSW search local while sending only Top-K candidates to Nemotron produced the desired separation between scale and reasoning cost.

### Dynamic catalog correctness

Agent catalogs change. CentRI therefore fingerprints the catalog and embedding configuration, rejects stale indexes, versions corrections, deduplicates feedback, and writes index artifacts atomically.

## Accomplishments that we're proud of

CentRI is a working routing platform rather than a single classifier:

- Offline semantic capability compilation.
- Contrastive hard-negative generation.
- HNSW and exact FAISS index modes.
- Two-stage retrieve-and-rerank routing.
- NVIDIA Nemotron integration through Nebius Token Factory.
- Multi-intent sharding and concurrent execution.
- Generic HTTP agent handoff with explicit mock fallback.
- Abstention and catalog-policy enforcement.
- JWT roles, approval gates, and redacted telemetry.
- Workflow dependency ordering.
- Reproducible routing and scale benchmarks.

### Current measured evidence

On 20 synthetic golden cases across 10 sample agents, the latest captured run achieved:

- **80% overall top-1 routing accuracy**
- **100% candidate recall@K**
- **80% automatic-route coverage**
- **100% selective accuracy** among automatic routes
- **3.09-second mean latency**
- **5.53-second p95 latency**

Every automatic route in the captured run was correct; uncertain cases abstained. A prompt-all Nemotron baseline achieved 70% accuracy and 70% coverage on the same cases. The dataset is intentionally small, so these are directional engineering measurements rather than universal production claims.

## What we learned

The most important lesson was that retrieval recall sets the upper bound for downstream routing:

\[
\text{reranker accuracy} \leq \text{candidate recall@K}
\]

If the correct agent is absent from the candidate set, no reranker can recover it. This makes query-bank quality, contrastive examples, embedding consistency, and index evaluation central to the system.

We also learned that enterprise routing must optimize for **safe coverage**, not forced classification. A calibrated abstention is preferable to an incorrect handoff when an agent can access sensitive data or perform a side effect.

Finally, the important scaling unit is not the number of agents visible to the model. It is the number of candidates that require model reasoning after semantic retrieval. That is the core reason CentRI can target much larger agent networks without making the GPU decision context grow linearly with the catalog.

## What's next for CentRI

The next phase is validation against larger human-authored datasets and catalogs containing 1,000, 10,000, and eventually millions of agents. The roadmap includes:

- distributed HNSW sharding and catalog partitioning
- stronger confidence calibration and abstention policies
- embedding and routing-card caching
- durable workflow state and retry semantics
- richer tenant isolation and authorization
- production tracing and metrics backends
- real agent runtimes with live tools and knowledge sources
- load testing across catalog size, shard count, GPU concurrency, and tenants

The long-term goal is an enterprise semantic API gateway that makes approved agents, proprietary data access, tools, and organizational expertise available to every authorized user through one accurate, governed, and scalable routing layer.
