# 2:50 CentRI Render demo script

Live demo URL:

```text
https://centri-demo.onrender.com
```

Use Postman with the Render-ready cURLs in `postman_test.txt`. Keep all keys
hidden on screen.

## 0:00-0:15 - Problem

Say:

> Enterprise agent catalogs grow faster than a single router prompt can stay
> accurate. CentRI gives the catalog one intelligent front door.

## 0:15-0:30 - Architecture

Show the architecture slide and say:

> CentRI compiles agent capability offline, searches local HNSW routing memory,
> and sends only a small candidate set to NVIDIA Nemotron on Nebius GPUs.

## 0:30-0:55 - Route a request

In Postman, call `POST /route`:

```json
{"query":"My VPN stopped after a password change."}
```

Point out `agent_id`, `agent_name`, candidates, confidence, and rationale.

Say:

> The gateway returns the exact agent ID required for the next handoff.

## 0:55-1:25 - Show how to test the deployment

First call:

```bash
curl https://centri-demo.onrender.com/health
```

Say:

> Render's free service may cold-start. Run health first and wait for the
> service to wake. The health response also returns ready-to-run test cURLs.

Then show `postman_test.txt`, import it into Postman, and point out that the
requests target `https://centri-demo.onrender.com`, not localhost.

## 1:25-1:45 - Run chat and Tavily

Call `POST /chat`:

```json
{
  "prompt":"What are the latest enterprise security updates relevant to our IT policy?",
  "use_web_search":true,
  "approval_granted":true
}
```

Show `web_research.status = "ok"` and the returned sources.

Say:

> CentRI can invoke Tavily at runtime for freshness-sensitive requests and pass
> the research context into the selected agent handoff.

## 1:45-2:05 - Compound intent

Call `POST /route`:

```json
{"query":"Analyze cloud infrastructure spend and prepare an incident summary."}
```

Show multiple `routes[]` entries.

Say:

> Compound requests are split into independently routable shards. Chat can
> execute independent shards concurrently and synthesize the results.

## 2:05-2:30 - Scale and evidence

Show the benchmark slide:

```text
100% candidate recall
100% selective accuracy
80% automatic coverage
3.09s mean latency
5.53s p95 latency
```

Say:

> The captured run routed every automatic decision correctly and abstained on
> uncertain cases. The larger-scale thesis is that the model sees Top-K cards,
> not the entire enterprise catalog.

## 2:30-2:50 - Close

Say:

> CentRI turns an expanding enterprise agent network into a semantic API:
> one request enters, the right agent ID comes out, and approved enterprise
> capabilities become efficiently available to authorized users.

Presenter checklist:

- Wake Render with `/health` before recording.
- Do not show `.env` or API keys.
- Be transparent that sample agents return `simulated` without live runtime endpoints.
- If Render is asleep, wait for the cold start before continuing.
