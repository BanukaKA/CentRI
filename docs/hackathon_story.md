# CentRI System Story

## Inspiration

As an Applied AI Engineer working on agentic systems that operate at global scale, I have seen
how quickly coordination becomes the bottleneck when the number of services,
capabilities, and possible destinations grows. Agent networks create the same
problem: users need one simple entry point, while the platform may contain
thousands of specialized agents. Imagine this not just at the level of a few hundred agents but 1000-10000s or even millions of micro agents. That's what CentRI solves with scale as the ultimate focus. 

I wanted to explore an independent solution focused on both speed and
accuracy not scale alone. CentRI is my own architecture and implementation,
built around a simple idea: compile agent capabilities into hyper efficient semantic routing
memory, retrieve only the relevant candidates, and reason narrowly over the
remaining ambiguity.

## What it does

CentRI is a semantic API gateway for agent networks.

It:

- Accepts one user request through a unified gateway.
- Splits compound requests into independent intents.
- Retrieves likely agents using local HNSW vector search.
- Uses NVIDIA Nemotron through Nebius Token Factory to rerank only the
  highest-value candidates.
- Returns the agent ID and name required for handoff.
- Supports concurrent multi-agent execution, abstention, approval gates, and
  feedback-based routing correction.

The result is a single routing contract:

```text
user request → CentRI → agent_id → authorized agent runtime
```

## How we built it

The system has an offline compilation plane and a runtime routing plane. Instead of at agent retrieval/routing runtime CentRI shifts all the heavy work to this stage.

During compilation, CentRI reads the agent registry, generates diverse and
contrastive routing examples, creates embeddings with
`Qwen/Qwen3-Embedding-8B`, and stores them in an HNSW/FAISS index.

At runtime, the gateway uses FastAPI, splits compound intent when necessary,
embeds the request, retrieves candidates locally, and sends only compact
routing cards to NVIDIA Nemotron Nano on Nebius. A generic asynchronous HTTP
adapter then hands the request to the selected agent runtime.

The platform also includes Tavily-assisted offline query generation, JWT
protection, redacted telemetry, workflow ordering, human-approval gates, and
golden-case evaluation.

## Challenges we ran into

The hardest problems were semantic collisions and uncertainty. Several agents
can legitimately share vocabulary, so simple keyword matching is not enough.
We addressed this with contrastive examples, candidate retrieval, focused
reranking, catalog exclusions, and explicit abstention.

We also had to separate local routing speed from GPU inference. The routing
memory and HNSW search remain local to the gateway, while Nemotron receives
only a bounded candidate context through Nebius. This keeps the reasoning
surface small without giving up model quality.

## Accomplishments that we're proud of

CentRI now provides a complete working routing platform rather than a single
classifier:

- Offline semantic capability compilation.
- HNSW and exact FAISS index modes.
- Two-stage retrieve-and-rerank routing.
- Compound-intent sharding and concurrent execution.
- NVIDIA Nemotron integration through Nebius Token Factory.
- HTTP agent handoff with mock fallback.
- Abstention, JWT roles, approval gates, and redacted telemetry.
- Reproducible benchmark and evaluation tooling.

On the current 20-case synthetic benchmark, CentRI achieved 100% candidate
recall and 100% selective accuracy: every automatic route was correct, while
uncertain cases abstained.

## What we learned

The most important lesson was that retrieval recall sets the upper bound for
downstream routing accuracy. If the correct agent is absent from the candidate
set, no reranker can recover it.

We also learned that enterprise routing must optimize for safe coverage, not
just forced classification. A calibrated abstention is better than an
incorrect handoff, especially when agents can access sensitive data or
perform side effects.

Finally, the right scaling unit is not the number of agents visible to the
model. It is the number of candidates that require reasoning after semantic
retrieval.

## What's next for CentRI

The next step is to validate CentRI with larger human-authored datasets and
catalogs containing 1,000, 10,000, and eventually millions of agents. The
roadmap includes distributed HNSW sharding, stronger calibration, durable
workflow state, richer tenant isolation, and real production agent runtimes.

The long-term goal is an enterprise semantic API gateway that makes approved
agents, proprietary data access, tools, and organizational expertise
efficiently available to every authorized user through one accurate and
scalable routing layer.


## What's next for CentRI
The next step is to validate CentRI with larger human-authored datasets and
catalogs containing 1,000, 10,000, and eventually millions of agents. The
roadmap includes distributed HNSW sharding, stronger calibration, durable
workflow state, richer tenant isolation, and real production agent runtimes.

The long-term goal is an enterprise semantic API gateway that makes approved
agents, proprietary data access, tools, and organizational expertise
efficiently available to every authorized user through one accurate and
scalable routing layer.