# CentRI routing benchmark

This report is generated from the current repository benchmark:

```powershell
python -m scripts.benchmark_router --output data/benchmark_report.json
```

The source report is [`data/benchmark_report.json`](../data/benchmark_report.json).
It contains per-case predictions and the scale projection. The benchmark uses
the 20 synthetic golden cases in `sample_agent_router_dataset.json`, so these
results demonstrate the current routing behavior but are not a production
accuracy guarantee.

## Measured run

The run used:

- 10 catalog agents
- 20 catalog golden cases
- `Qwen/Qwen3-Embedding-8B` for embeddings
- NVIDIA Nemotron Nano served through Nebius Token Factory for intent/rerank
- HNSW FAISS index
- identical cases and environment for the measured baselines

### Results

| Baseline | Top-1 accuracy | Coverage | Selective accuracy | Candidate recall | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| CentRI retrieve → rerank → abstain | 80% | 80% | 100% | 100% | 3.09 s | 5.53 s |
| Prompt-all Nemotron | 70% | 70% | 100% | not applicable | 1.46 s | 2.00 s |
| Deterministic lexical overlap | 80% | 100% | 80% | not applicable | 0.29 ms | 0.31 ms |

Definitions:

- **Top-1 accuracy:** correct agent divided by all cases; abstentions count as
  not routed.
- **Coverage:** fraction of cases for which a baseline returned a route.
- **Selective accuracy:** correctness among routed, non-abstained cases.
- **Candidate recall:** whether the correct agent appeared in CentRI's
  retrieved/rerank candidate set.

### Interpretation

The meaningful CentRI result is not “every request is faster.” In this run,
the simple lexical baseline is fastest and the prompt-all LLM has lower
single-request latency because it makes fewer model calls. CentRI's measured
strength is the quality/safety trade-off:

- It retrieved the correct agent into the candidate set for all 20 cases.
- It made no incorrect automatic route in this run; the four uncertain cases
  abstained instead.
- It achieved 100% selective accuracy at 80% coverage.
- The prompt-all baseline automatically routed fewer cases and covered 70%.
- The lexical baseline covered everything but made four domain-confusion
  errors.

The benchmark is small and model responses can vary. Repeat it across multiple
seeds, larger real-world query sets, and catalog sizes before publishing a
general accuracy or latency claim.

### Domain-level behavior

Each sample agent has two cases, so domain-level results are directional rather
than statistically meaningful. In the captured run, CentRI routed all cases
for IT service desk, finance AP, HR policy, commercial contracts, customer
support, and compliance. Engineering incidents, marketing content, product
backlog, and sales research each had one abstention and one correct route.
Every non-abstained domain case was correct.

## Why routing scales

The benchmark estimates how much agent-schema context each architecture
would expose to a request. These are context projections, not latency
measurements:

- Prompt-all context grows approximately with `agent_count × schema_tokens`.
- CentRI reranker context stays near `Top-K × routing_card_tokens`.
- The local HNSW routing plane searches a graph rather than placing every
  agent schema into the Nemotron prompt.
- Nemotron still runs on NVIDIA GPUs through Nebius, but the GPU decision
  stage receives only the bounded candidate set.

At 1,000–10,000 or even millions of agents, a flat typed-choice call is not an
efficient catalog-discovery architecture: the full option surface must be
serialized, maintained, and evaluated as one closed choice space. CentRI
compiles the catalog into local semantic memory, then keeps runtime
disambiguation bounded by Top-K. Catalog partitioning, HNSW/ANN sharding,
cache locality, and parallel intent routing are the scale path.

Run the benchmark to view the exact projections for 10, 100, 1,000, and
10,000 agents:

```powershell
python -m scripts.benchmark_router
```

