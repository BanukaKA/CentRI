"""
Offline compilation: synthetic query expansion, embedding, FAISS indexing.

Usage:
  python -m scripts.compile
  python -m scripts.compile --synthesize   # requires NEBIUS_API_KEY
"""

from __future__ import annotations

import argparse
import sys

from centri.clients.nebius import NebiusClient
from centri.clients.tavily import TavilyClient
from centri.config import get_settings
from centri.index.store import VectorIndex, VectorRecord
from centri.registry import load_catalog
from centri.synthesis.query_generator import build_full_query_bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile CentRI vector routing index")
    parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Call Nebius LLM for full synthetic query bank (contrastive expansion)",
    )
    parser.add_argument(
        "--force-synthesize",
        action="store_true",
        help="Ignore cached synthetic_queries.json and regenerate",
    )
    args = parser.parse_args()

    settings = get_settings()
    catalog = load_catalog(settings.centri_agent_catalog)
    tavily = TavilyClient(settings)

    if not settings.nebius_api_key:
        print("NEBIUS_API_KEY required to embed and build the FAISS index.", file=sys.stderr)
        sys.exit(1)

    nebius = NebiusClient(settings)
    synth_client: NebiusClient | None = nebius if args.synthesize else None
    if not args.synthesize:
        print("Using catalog seed queries (pass --synthesize for contrastive LLM expansion).")

    cached_path = settings.queries_path
    if args.force_synthesize and cached_path.exists():
        cached_path.unlink()

    bank = build_full_query_bank(catalog, synth_client, tavily, settings, cached_path)

    records: list[VectorRecord] = []
    for agent in catalog.agents:
        queries = bank.get(agent.agent_id, [])
        seeds = set(agent.routing.get("example_queries") or [])
        for q in queries:
            source = "seed" if q in seeds else "synthetic"
            records.append(VectorRecord(agent_id=agent.agent_id, query_text=q, source=source))

    if not records:
        print("No queries to index.", file=sys.stderr)
        sys.exit(1)

    index = VectorIndex(settings)
    print(f"Embedding {len(records)} queries with {settings.centri_embedding_model}...")
    index.build_from_records(nebius, records)
    index.save()
    print(f"Wrote FAISS index to {settings.index_path}")
    print(f"Metadata: {settings.metadata_path}")
    print(f"Query bank: {settings.queries_path}")


if __name__ == "__main__":
    main()
