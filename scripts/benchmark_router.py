"""Benchmark CentRI against transparent routing baselines.

Measured baselines:
  - centri: retrieval + Nemotron split/rerank + abstention
  - lexical: deterministic keyword/example overlap
  - prompt_all: one Nebius LLM call with the complete catalog

Optional external adapters:
  - jev: set CENTRI_JEV_URL and CENTRI_JEV_API_KEY
  - clef: set CENTRI_CLEF_URL and CENTRI_CLEF_API_KEY

The report separates measured values from scale projections. It never invents
Jev or Cloudflare values when credentials are unavailable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import httpx

from centri.clients.nebius import NebiusClient
from centri.config import Settings, get_settings
from centri.index.store import VectorIndex
from centri.registry import AgentCatalog, AgentRecord, load_catalog
from centri.routing.pipeline import CentRIRouter
from scripts.evaluate_routing import golden_cases


def tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
    }


def agent_search_text(agent: AgentRecord) -> set[str]:
    routing = agent.routing or {}
    values = [
        agent.name,
        agent.description,
        agent.domain,
        " ".join(agent.tags),
        " ".join(routing.get("keywords") or []),
        " ".join(routing.get("intent_labels") or []),
        " ".join(routing.get("example_queries") or []),
    ]
    return tokens(" ".join(values))


def lexical_route(query: str, catalog: AgentCatalog) -> str | None:
    query_tokens = tokens(query)
    scored: list[tuple[float, int, str]] = []
    for agent in catalog.agents:
        overlap = len(query_tokens & agent_search_text(agent))
        coverage = overlap / max(len(query_tokens), 1)
        priority = int((agent.routing or {}).get("priority", 0))
        scored.append((coverage, priority, agent.agent_id))
    scored.sort(reverse=True)
    return scored[0][2] if scored and scored[0][0] > 0 else None


def cards(catalog: AgentCatalog) -> str:
    return "\n\n---\n\n".join(agent.routing_card() for agent in catalog.agents)


def prompt_all_route(query: str, catalog: AgentCatalog, client: NebiusClient, settings: Settings) -> str | None:
    system = (
        "You are a single-pass enterprise agent router. Select exactly one "
        "agent_id from the catalog. Return strict JSON with agent_id and confidence."
    )
    user = (
        f"User query:\n{query}\n\nComplete agent catalog:\n{cards(catalog)}\n\n"
        'Return {"agent_id":"...", "confidence":0.0}.'
    )
    try:
        result = client.chat_json(
            system,
            user,
            model=settings.centri_llm_model,
            temperature=0.0,
            max_tokens=512,
        )
        candidate = result.get("agent_id")
        return candidate if catalog.by_id(candidate) else None
    except Exception:
        return None


def parse_decision_response(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("agent_id"),
        payload.get("choice"),
        (payload.get("answer") or {}).get("choice")
        if isinstance(payload.get("answer"), dict)
        else None,
    ]
    answers = payload.get("answers")
    if isinstance(answers, dict):
        route = answers.get("route") or answers.get("agent")
        if isinstance(route, dict):
            candidates.extend([route.get("choice"), route.get("agent_id")])
        elif isinstance(route, str):
            candidates.append(route)
    result = payload.get("result")
    if isinstance(result, dict):
        candidates.extend([result.get("choice"), result.get("agent_id")])
    return next((str(value) for value in candidates if value), None)


def external_decision(
    url: str,
    api_key: str,
    model: str,
    query: str,
    catalog: AgentCatalog,
) -> str | None:
    if not url or not api_key:
        return None
    options = {
        agent.agent_id: f"{agent.name}: {agent.description}"
        for agent in catalog.agents
    }
    payload = {
        "model": model,
        "state": {"query": query, "agents": options},
        "questions": {
            "route": {
                "type": "choice",
                "options": options,
            }
        },
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        result = parse_decision_response(response.json())
    return result if catalog.by_id(result) else None


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = sorted(row["latency_ms"] for row in rows)
    p95_index = min(len(latencies) - 1, max(0, math.ceil(len(latencies) * 0.95) - 1))
    return {
        "status": "measured",
        "cases": len(rows),
        "accuracy": mean(row["correct"] for row in rows) if rows else 0.0,
        "abstention_rate": mean(row["abstained"] for row in rows) if rows else 0.0,
        "coverage": mean(not row["abstained"] for row in rows) if rows else 0.0,
        "selective_accuracy": (
            mean(row["correct"] for row in rows if not row["abstained"])
            if any(not row["abstained"] for row in rows)
            else 0.0
        ),
        "error_rate": mean(row["error"] for row in rows) if rows else 0.0,
        "mean_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "p95_latency_ms": round(latencies[p95_index], 2) if latencies else 0.0,
        "confusion_pairs": dict(
            Counter(
                f"{row['expected_agent_id']} -> {row['predicted_agent_id']}"
                for row in rows
                if not row["correct"] and not row["abstained"]
            )
        ),
    }


def run_baseline(
    name: str,
    cases: list[dict[str, Any]],
    route_fn: Callable[[str], str | None],
) -> dict[str, Any]:
    rows = []
    for case in cases:
        started = time.perf_counter()
        error = False
        try:
            predicted = route_fn(str(case["input"]))
        except Exception:
            predicted = None
            error = True
        elapsed = (time.perf_counter() - started) * 1000
        abstained = predicted is None and not error
        rows.append(
            {
                "case_id": case.get("case_id"),
                "expected_agent_id": case["expected_agent_id"],
                "predicted_agent_id": predicted,
                "correct": predicted == case["expected_agent_id"],
                "abstained": abstained,
                "error": error,
                "latency_ms": round(elapsed, 2),
            }
        )
    grouped = {}
    for agent_id in sorted({row["expected_agent_id"] for row in rows}):
        grouped[agent_id] = metrics(
            [row for row in rows if row["expected_agent_id"] == agent_id]
        )
    return {"name": name, "metrics": metrics(rows), "by_expected_agent": grouped, "cases": rows}


def run_centri(
    cases: list[dict[str, Any]],
    router: CentRIRouter,
) -> dict[str, Any]:
    rows = []
    for case in cases:
        started = time.perf_counter()
        error = False
        try:
            decision = router.route(str(case["input"])).decisions[0]
            predicted = decision.agent_id
            abstained = decision.abstained
            recall_at_k = case["expected_agent_id"] in {
                item["agent_id"] for item in decision.candidates
            }
        except Exception:
            predicted = None
            abstained = False
            recall_at_k = False
            error = True
        rows.append(
            {
                "case_id": case.get("case_id"),
                "expected_agent_id": case["expected_agent_id"],
                "predicted_agent_id": predicted,
                "correct": predicted == case["expected_agent_id"],
                "abstained": abstained,
                "error": error,
                "recall_at_k": recall_at_k,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
    grouped = {}
    for agent_id in sorted({row["expected_agent_id"] for row in rows}):
        grouped[agent_id] = metrics(
            [row for row in rows if row["expected_agent_id"] == agent_id]
        )
    output = {
        "name": "centri",
        "metrics": metrics(rows),
        "by_expected_agent": grouped,
        "cases": rows,
    }
    output["metrics"]["candidate_recall_at_k"] = mean(
        row["recall_at_k"] for row in rows
    ) if rows else 0.0
    return output


def scale_projection(settings: Settings, catalog: AgentCatalog, index: VectorIndex) -> list[dict[str, Any]]:
    average_card_chars = mean(len(agent.routing_card()) for agent in catalog.agents)
    dimension = index.dim or 1536
    rows = []
    for agent_count in (10, 100, 1000, 10000):
        prompt_tokens = math.ceil((average_card_chars * agent_count) / 4)
        candidate_tokens = math.ceil(
            (average_card_chars * settings.centri_top_k_agents_rerank) / 4
        )
        rows.append(
            {
                "agent_count": agent_count,
                "prompt_all_catalog_tokens_estimate": prompt_tokens,
                "centri_rerank_tokens_estimate": candidate_tokens,
                "catalog_context_reduction_factor": round(prompt_tokens / max(candidate_tokens, 1), 2),
                "flat_distance_terms_per_query": agent_count
                * settings.centri_queries_per_agent
                * dimension,
                "interpretation": "projection, not a measured latency",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark CentRI routing baselines")
    parser.add_argument("--output", type=Path, default=Path("data/benchmark_report.json"))
    parser.add_argument(
        "--baselines",
        default="centri,lexical,prompt_all,jev,clef",
        help="Comma-separated baseline names",
    )
    args = parser.parse_args()

    settings = get_settings()
    catalog = load_catalog(settings.centri_agent_catalog)
    cases = golden_cases(catalog)
    index = VectorIndex(settings)
    index.load(
        expected_manifest={
            "catalog_fingerprint": catalog.fingerprint(),
            "embedding_model": settings.centri_embedding_model,
        }
    )
    requested = {name.strip() for name in args.baselines.split(",")}
    report: dict[str, Any] = {
        "metadata": {
            "dataset": settings.centri_agent_catalog.name,
            "agents": len(catalog.agents),
            "cases": len(cases),
            "embedding_model": settings.centri_embedding_model,
            "decision_model": settings.centri_llm_model,
            "index_type": index.index_type,
            "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "methodology": "Synthetic catalog golden cases; measured values are not production-scale guarantees.",
        },
        "baselines": {},
        "scale_projection": scale_projection(settings, catalog, index),
        "external_comparison_notes": {
            "jev": "Not measured unless CENTRI_JEV_URL and CENTRI_JEV_API_KEY are configured. Public Jev claims are documented separately and are not substituted for measurements.",
            "cloudflare_clef": "Not measured unless CENTRI_CLEF_URL and CENTRI_CLEF_API_KEY are configured. Clef is a decision model; Cloudflare AI Search/Vectorize are separate retrieval products.",
        },
    }

    if "centri" in requested:
        nebius = NebiusClient(settings)
        report["baselines"]["centri"] = run_centri(cases, CentRIRouter(settings, catalog, index, nebius))
    if "lexical" in requested:
        report["baselines"]["lexical"] = run_baseline(
            "lexical", cases, lambda query: lexical_route(query, catalog)
        )
    if "prompt_all" in requested:
        if settings.nebius_api_key:
            client = NebiusClient(settings)
            report["baselines"]["prompt_all"] = run_baseline(
                "prompt_all",
                cases,
                lambda query: prompt_all_route(query, catalog, client, settings),
            )
        else:
            report["baselines"]["prompt_all"] = {"name": "prompt_all", "metrics": {"status": "not_measured"}}
    for name, url, key, model in (
        ("jev", settings.centri_jev_url, settings.centri_jev_api_key, settings.centri_jev_model),
        ("clef", settings.centri_clef_url, settings.centri_clef_api_key, settings.centri_clef_model),
    ):
        if name in requested:
            if url and key:
                report["baselines"][name] = run_baseline(
                    name,
                    cases,
                    lambda query, u=url, k=key, m=model: external_decision(
                        u, k, m, query, catalog
                    ),
                )
            else:
                report["baselines"][name] = {
                    "name": name,
                    "metrics": {
                        "status": "not_measured",
                        "reason": "No authenticated comparison endpoint configured",
                    },
                }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["baselines"], indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
