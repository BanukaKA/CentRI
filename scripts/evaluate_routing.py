"""Evaluate CentRI against the catalog's golden routing cases.

Full evaluation requires NEBIUS_API_KEY and a compiled index:
    python -m scripts.evaluate_routing

Catalog-only validation does not call external services:
    python -m scripts.evaluate_routing --catalog-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from centri.clients.nebius import NebiusClient
from centri.config import get_settings
from centri.index.store import VectorIndex
from centri.registry import AgentCatalog, load_catalog
from centri.routing.pipeline import CentRIRouter


def golden_cases(catalog: AgentCatalog) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for agent in catalog.agents:
        for case in (agent.raw.get("evaluation") or {}).get("golden_test_cases") or []:
            expected = case.get("expected_agent_id", agent.agent_id)
            if not case.get("expected_agent_id"):
                expected = agent.agent_id
            cases.append(
                {
                    **case,
                    "expected_agent_id": expected,
                    "source_agent_id": agent.agent_id,
                }
            )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate CentRI routing")
    parser.add_argument("--catalog-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    settings = get_settings()
    catalog = load_catalog(settings.centri_agent_catalog)
    cases = golden_cases(catalog)
    if args.catalog_only:
        print(json.dumps({"cases": len(cases), "agents": len(catalog.agents)}, indent=2))
        return
    if not settings.nebius_api_key:
        print("NEBIUS_API_KEY is required for full routing evaluation", file=sys.stderr)
        raise SystemExit(1)

    index = VectorIndex(settings)
    index.load(
        expected_manifest={
            "catalog_fingerprint": catalog.fingerprint(),
            "embedding_model": settings.centri_embedding_model,
        }
    )
    router = CentRIRouter(settings, catalog, index, NebiusClient(settings))
    rows: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        result = router.route(str(case["input"]))
        elapsed_ms = (time.perf_counter() - started) * 1000
        decision = result.decisions[0]
        candidates = [item["agent_id"] for item in decision.candidates]
        predicted = decision.agent_id
        expected = case["expected_agent_id"]
        rows.append(
            {
                "case_id": case.get("case_id"),
                "input": case["input"],
                "expected_agent_id": expected,
                "predicted_agent_id": predicted,
                "correct": predicted == expected,
                "recall_at_k": expected in candidates,
                "abstained": decision.abstained,
                "confidence": decision.confidence,
                "similarity": decision.similarity,
                "margin": decision.margin,
                "latency_ms": round(elapsed_ms, 2),
                "candidates": candidates,
            }
        )

    latencies = sorted(row["latency_ms"] for row in rows)
    p95_index = min(len(latencies) - 1, max(0, int(len(latencies) * 0.95) - 1))
    summary = {
        "agents": len(catalog.agents),
        "cases": len(rows),
        "top1_accuracy": mean(row["correct"] for row in rows) if rows else 0.0,
        "recall_at_k": mean(row["recall_at_k"] for row in rows) if rows else 0.0,
        "abstention_rate": mean(row["abstained"] for row in rows) if rows else 0.0,
        "mean_latency_ms": mean(latencies) if latencies else 0.0,
        "p95_latency_ms": latencies[p95_index] if latencies else 0.0,
        "confusion_pairs": Counter(
            f"{row['expected_agent_id']} -> {row['predicted_agent_id']}"
            for row in rows
            if not row["correct"]
        ),
    }
    output = {"summary": summary, "cases": rows}
    print(json.dumps(output, indent=2, default=dict))
    if args.output:
        args.output.write_text(json.dumps(output, indent=2, default=dict), encoding="utf-8")


if __name__ == "__main__":
    main()
