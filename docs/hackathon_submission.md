# Nebius x NVIDIA Global AI Hackathon submission draft

This document is the submission-ready narrative and checklist for CentRI. It
is written for the **Best Apps and Agents** track, with the **Coding and
Agentic Engineering** track as a possible alternative if the demo emphasizes
developer tooling and agent infrastructure.

## Project title

**CentRI — The semantic API gateway for agent swarms**

## Event positioning

- Submission deadline in the official rules: **October 30, 2026 at 10:00 AM
  PT / 1:00 PM EDT**. Verify the live Devpost page immediately before
  submitting.
- Recommended track: **Best Apps and Agents**
- Alternative track: **Coding and Agentic Engineering** if the final demo
  emphasizes developer-facing agent infrastructure.
- Relevant prize context: the event lists Grand Prize, second-place,
  third-place, track prizes, and a Best Use of Tavily prize. The current
  submission is specifically designed to demonstrate both Nebius Token
  Factory and Tavily usage.

## One-line pitch

CentRI gives thousands of specialized AI agents one intelligent front door:
it compiles agent capability into semantic routing memory offline, retrieves
high-recall candidates in milliseconds, and uses NVIDIA Nemotron on Nebius only
to resolve the remaining ambiguity.

The routing memory and candidate search are local to the CentRI control plane;
Nemotron inference runs on NVIDIA GPU infrastructure through Nebius. This
separation lets enterprise networks share one organization’s approved agents,
proprietary data access, and operational resources efficiently with every
authorized user without placing the entire catalog into every prompt.

## The problem

The next generation of enterprise software will not expose one chatbot. It
will expose a catalog of specialized agents for IT, finance, legal, HR,
support, engineering, compliance, sales, product, and marketing.

Without a routing control plane, every request faces one of three bad choices:

- Put the entire catalog into an LLM prompt. Context, cost, and ambiguity grow
  with every new agent.
- Train a closed classifier. Every agent addition or taxonomy change requires
  labeled data and retraining.
- Give a typed decision model the entire choice set. That works for bounded
  decisions, but it does not create an open-world catalog memory, compound
  intent handling, or agent lifecycle governance.

CentRI separates the discovery problem from the decision problem.

## What we built

CentRI is a FastAPI semantic gateway with three planes:

1. **Offline compiler:** reads the agent registry, expands each agent into
   synthetic and contrastive user utterances, embeds them through Nebius, and
   builds an HNSW/Flat FAISS index.
2. **Runtime router:** splits compound requests, embeds each shard, retrieves
   Top-K vectors, aggregates agent evidence, and gives only the Top-3 routing
   cards to NVIDIA Nemotron Nano for disambiguation.
3. **Learning/governance loop:** records redacted routing telemetry, supports
   reviewed correction vectors, abstains under uncertainty, and protects
   operations with JWT roles and approval gates.

The gateway returns agent IDs and names through `/route`, can execute configured
HTTP agent runtimes through `/chat`, and can synthesize independent results for
compound requests.

## Why the idea is non-obvious

The innovation is not “use embeddings to classify text.” The innovation is the
system boundary:

```text
Agent catalog changes
    → semantic capability compilation
    → persistent routing memory
    → bounded candidate retrieval
    → focused decision model
    → governed agent handoff
```

CentRI turns the agent catalog into an **addressable semantic API surface**.
The LLM is no longer asked to rediscover the entire organization on every
request. It is used as a precision instrument only after retrieval has reduced
the decision surface.

The system also handles the two routing failures that become dominant at
scale:

- **Semantic collisions:** adjacent agents receive contrastive examples and
  are disambiguated from compact routing cards.
- **Compound intents:** one request is sharded into independent tasks and
  routed concurrently.

## Nebius and NVIDIA usage

The current configuration uses:

- Nebius Token Factory OpenAI-compatible API
- `Qwen/Qwen3-Embedding-8B` for dense embeddings
- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` for runtime intent splitting and
  stage-two routing
- `nvidia/nemotron-3-super-120b-a12b` for optional offline synthesis and
  compound-result synthesis
- Tavily for fresh-context synthetic generation and live `/chat` research
  requests through `use_web_search: true`

This satisfies the core design requirement to run on Nebius Token Factory and
use an NVIDIA open-source model. For the final submission, capture a short
screen recording or log excerpt showing the Nemotron model IDs and Nebius
Token Factory endpoint in the running demo.

Recommended production demo deployment:

```text
Nebius Token Factory / Serverless Endpoint
    → CentRI FastAPI gateway
    → configured agent HTTP runtimes
```

Nebius Serverless Jobs are a natural follow-on for nightly correction,
large-scale compilation, and benchmark runs.

## Measured evidence

The current reproducible benchmark is in
[`docs/benchmark_report.md`](benchmark_report.md) and
[`data/benchmark_report.json`](../data/benchmark_report.json).

On the 20 synthetic golden cases in the sample catalog, the latest measured
run showed:

- CentRI top-1 accuracy: **80%**
- CentRI candidate recall: **100%**
- CentRI coverage: **80%**
- CentRI selective accuracy: **100%**
- CentRI mean latency: **3.09 seconds**
- CentRI p95 latency: **5.53 seconds**
- Prompt-all Nemotron accuracy: **70%**
- Prompt-all Nemotron coverage: **70%**
- Lexical baseline accuracy: **80%**, with four domain-confusion errors

These numbers are a transparent early benchmark, not a universal claim. The
submission should present the benchmark as evidence of the routing architecture
and include a plan to expand the evaluation set. The latest run had 100%
selective accuracy: every automatic route was correct, while uncertain cases
abstained.

At 1,000–10,000 or even millions of agents, a flat typed-choice decision call
is not an efficient catalog-discovery architecture: the option surface must be
serialized, maintained, and evaluated as one closed choice space. CentRI
separates discovery from choice, so the local routing plane can grow the
catalog while the Nemotron decision stage stays bounded to a small candidate
set. HNSW/ANN indexing, sharding, and catalog partitioning are the path to
that scale; the exact p95 curve must be measured on the target deployment.

## Business impact

CentRI is aimed at organizations operating an internal agent marketplace.
Potential users include:

- shared-services organizations routing employee requests
- enterprises with multiple compliance and approval agents
- platform teams exposing tools through agent APIs
- BPO and customer operations teams with many domain-specific workers
- developers building agent swarms whose catalogs change weekly

The economic value is reducing repeated LLM catalog inspection, avoiding
wrong-agent handoffs, making new agents discoverable immediately after
compilation, and creating an auditable routing layer independent of the
downstream agent implementation.

## Development history statement

Use this first-person statement in the submission if it accurately reflects
the author's history:

> I have worked on CentRI for at least one month, iterating from a semantic
> routing idea into a working open-infrastructure prototype. During the
> submission period I added the offline compiler, contrastive query
> generation, Nebius embeddings, NVIDIA Nemotron routing, HNSW indexing,
> compound-intent orchestration, abstention, HTTP handoff, evaluation,
> telemetry redaction, and the submission benchmark.

## Three-minute demo storyline

1. Show the 10-agent catalog and explain that the same registry shape scales
   to a much larger enterprise catalog.
2. Run `python -m scripts.compile` and show the HNSW index, manifest, and
   vector metadata.
3. Open `/docs` and call `POST /route` with a VPN request.
4. Show the selected agent ID, Top-3 candidates, similarity, margin, and
   Nemotron reranking rationale.
5. Submit a compound request and show multiple intent shards.
6. Call `/chat` with `approval_granted=true` and show the explicit simulated
   fallback or a configured HTTP agent response.
7. Run `python -m scripts.benchmark_router` and show the accuracy, coverage,
   candidate recall, and p95 metrics.
8. End with the message: “CentRI is the control plane that lets the agent
   catalog grow without putting the entire catalog in every prompt.”

## Submission checklist

### Required by the event

- [x] Public open-source license in the repository: MIT
- [x] README with setup and run instructions
- [x] Working source code
- [x] Nebius Token Factory integration
- [x] NVIDIA open-source model integration: Nemotron
- [x] Project description and technical architecture
- [ ] Public GitHub/GitLab/Bitbucket repository URL
- [ ] Public working demo URL or hosted test build
- [ ] Public YouTube demo video, three minutes or less
- [x] Functional Tavily runtime path demonstrated through `/chat`
- [ ] Final feedback on Nebius, NVIDIA, and Tavily usage
- [ ] Track selection in Devpost

### Recommended before submission

- [ ] Configure at least one real HTTP agent runtime for the demo
- [ ] Deploy the gateway and model call through Nebius infrastructure
- [ ] Add a live demo health URL and stable demo credentials
- [ ] Run the benchmark multiple times and report variance
- [ ] Add more than 20 human-authored routing cases
- [ ] Record Nebius/Nemotron evidence in the demo video
- [ ] Rotate all development API keys before publishing the repository

## Official event references

- [Hackathon landing page](https://nebiusglobalaihackathon.devpost.com)
- [Official rules](https://nebiusglobalaihackathon.devpost.com/rules)
- [Official FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs)
- [Nebius Token Factory documentation](https://docs.tokenfactory.nebius.com/)
- [Nebius serverless AI cookbook](https://github.com/nebius/serverless-ai-cookbook)

The event materials state that submissions must run on Nebius Token Factory or
Nebius AI Cloud and use at least one NVIDIA open-source model, and require a
public repository, open-source license, README, working demo, and short demo
video. Verify the live Devpost rules immediately before submission because
deadlines and organizer instructions can change.

