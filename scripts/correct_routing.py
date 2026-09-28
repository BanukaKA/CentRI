"""
Nightly-style space correction: read shadow logs for refused routes and
infer correct agent via capable LLM, then append vectors.

Usage:
  python -m scripts.correct_routing --date 2026-09-28
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from centri.clients.nebius import NebiusClient
from centri.config import get_settings
from centri.index.store import VectorIndex
from centri.registry import load_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD shadow log date")
    args = parser.parse_args()

    settings = get_settings()
    log_path = settings.centri_shadow_log_dir / f"shadow_{args.date}.jsonl"
    if not log_path.exists():
        raise SystemExit(f"No log at {log_path}")

    catalog = load_catalog(settings.centri_agent_catalog)
    nebius = NebiusClient(settings)
    index = VectorIndex(settings)
    index.load()

    cards = "\n\n".join(a.routing_card() for a in catalog.agents)
    corrected = 0
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row.get("agent_refused"):
                continue
            prompt = row.get("shard") or row.get("prompt")
            if not prompt:
                continue
            data = nebius.chat_json(
                system=(
                    "Pick the best agent_id for this user query. "
                    'Output JSON: {"agent_id": "...", "reason": "..."}'
                ),
                user=f"Query:\n{prompt}\n\nAgents:\n{cards}",
                model=settings.centri_llm_model_synthesis,
                temperature=0.0,
            )
            agent_id = data.get("agent_id")
            if catalog.by_id(agent_id):
                index.append_correction(nebius, agent_id, prompt)
                corrected += 1

    print(f"Appended {corrected} correction vectors.")


if __name__ == "__main__":
    main()
