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
| CentRI retrieve → rerank → abstain | 80% | 80% | 100% | 100% | 5.09 s | 7.58 s |
| Prompt-all Nemotron | 70% | 70% | 100% | not applicable | 2.09 s | 3.00 s |
| Deterministic lexical overlap | 80% | 100% | 80% | not applicable | 0.33 ms | 0.42 ms |

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
- It made no incorrect automatic route in this run; the five uncertain cases
  abstained instead.
- It achieved 100% selective accuracy at 85% coverage.
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

## Jev comparison

Jev / TypeSafe System One is a typed decision engine, not a vector catalog or
agent lifecycle system. Its `Choice`, `Score`, and `Noul` primitives are
well-suited to the final decision step after candidates have been discovered.
Public documentation and tooling describe a practical `Choice` option limit
of up to 255 options; this is an interface constraint, not a universal limit
on single-pass neural models.

A fair vanilla Jev comparison would:

1. Serialize all agent IDs and descriptions into a typed `Choice` question.
2. Call the Jev API for every golden query.
3. Record top-1 accuracy, coverage, confidence, end-to-end latency, and input
   tokens.
4. Repeat with 256+ agents using hierarchical retrieval because the flat
   choice surface is no longer sufficient.

No Jev credentials or endpoint were configured for this repository, therefore
the report intentionally records Jev as **not measured**. Configure:

```dotenv
CENTRI_JEV_URL=
CENTRI_JEV_API_KEY=
CENTRI_JEV_MODEL=jev-latest
```

Then rerun the benchmark. The adapter reports its actual response rather than
substituting vendor claims.

Research:

- [TypeSafe System One](https://docs.typesafe.ai/concepts/system-one)
- [TypeSafe API](https://docs.typesafe.ai/api)
- [TypeSafe Jev announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [Jev JSON Schema adapter](https://github.com/Kiln-AI/jev_jsonschema)

## Cloudflare Clef comparison

“Cloudflare Clef Search” is not a single product name in the public
documentation. The closest architecture is:

```text
Cloudflare Vectorize / AI Search
    → Cloudflare Clef or Clef-flash decision model
    → Worker/tool execution
```

Clef is a structured decision model. Cloudflare Vectorize and AI Search are
the retrieval/search components. This is complementary to CentRI rather than
a direct one-for-one replacement:

- Cloudflare provides a managed edge retrieval and decision stack.
- CentRI provides catalog compilation, contrastive routing memory,
  multi-intent sharding, agent-specific routing cards, provider adapters,
  abstention, and correction-index governance.
- CentRI can use a decision model such as Clef as its stage-two reranker if an
  adapter is configured.

No Cloudflare account or Clef endpoint was configured, so Clef is also
**not measured**. Configure:

```dotenv
CENTRI_CLEF_URL=
CENTRI_CLEF_API_KEY=
CENTRI_CLEF_MODEL=@cf/cloudflare/clef-flash
```

Research:

- [Cloudflare Clef](https://developers.cloudflare.com/workers-ai/models/clef)
- [Cloudflare Clef-flash](https://developers.cloudflare.com/workers-ai/models/clef-flash)
- [Cloudflare Clef announcement](https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai)
- [Cloudflare Vectorize limits](https://developers.cloudflare.com/vectorize/platform/limits)
- [Cloudflare AI Search limits and pricing](https://developers.cloudflare.com/ai-search/platform/limits-pricing)

## Scale projection

The benchmark also estimates how much agent-schema context each architecture
would expose to a request. These are token/context projections, not latency
measurements:

- Prompt-all context grows approximately with `agent_count × schema_tokens`.
- CentRI reranker context stays near `Top-K × routing_card_tokens`.
- Flat vector distance work grows with indexed vectors; HNSW is the
  production-oriented approximate index used here to reduce search work.

Run the benchmark to view the exact projections for 10, 100, 1,000, and
10,000 agents:

```powershell
python -m scripts.benchmark_router
```

