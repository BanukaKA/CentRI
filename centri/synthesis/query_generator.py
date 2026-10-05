from __future__ import annotations

import json
from pathlib import Path

from centri.clients.nebius import NebiusClient
from centri.clients.tavily import TavilyClient
from centri.config import Settings
from centri.registry import AgentCatalog, AgentRecord, adjacent_agents


def _needs_fresh_context(agent: AgentRecord) -> bool:
    knowledge = agent.knowledge or {}
    sources = knowledge.get("sources") or []
    min_sla = 365
    for src in sources:
        sla = src.get("freshness_sla_days")
        if isinstance(sla, int):
            min_sla = min(min_sla, sla)
    return min_sla <= 30


def _tavily_context(tavily: TavilyClient, agent: AgentRecord) -> str:
    if not tavily.enabled or not _needs_fresh_context(agent):
        return ""
    query = f"{agent.name} {agent.domain} recent updates industry news"
    try:
        results = tavily.search(query, max_results=4)
    except Exception:
        return ""
    if not results:
        return ""
    snippets = []
    for r in results:
        title = r.get("title", "")
        content = (r.get("content") or "")[:400]
        url = r.get("url", "")
        snippets.append(f"- {title}: {content} ({url})")
    return "Recent web context (use for timely phrasing only):\n" + "\n".join(snippets)


def bootstrap_seed_queries(agent: AgentRecord) -> list[str]:
    """Catalog-native seeds — always available without API keys."""
    queries: list[str] = []
    routing = agent.routing or {}
    for q in routing.get("example_queries") or []:
        queries.append(q)
    eval_block = agent.raw.get("evaluation") or {}
    for case in eval_block.get("golden_test_cases") or []:
        inp = case.get("input")
        if inp:
            queries.append(inp)
    # Light keyword expansions for PoC density
    for kw in (routing.get("keywords") or [])[:8]:
        queries.append(f"Help with {kw} issue at work.")
        queries.append(f"Northstar employee question about {kw}.")
    return list(dict.fromkeys(queries))


def generate_synthetic_queries(
    agent: AgentRecord,
    catalog: AgentCatalog,
    nebius: NebiusClient,
    tavily: TavilyClient,
    settings: Settings,
    count: int,
) -> list[str]:
    peers = adjacent_agents(agent, catalog, k=2)
    peer_cards = "\n\n---\n\n".join(p.routing_card() for p in peers)
    tavily_block = _tavily_context(tavily, agent)

    system = (
        "You generate realistic employee/user utterances for training a semantic router. "
        "Output strict JSON: {\"queries\": [\"...\"]}. "
        "Queries must be diverse (short keywords, full sentences, multi-step tasks). "
        "Do not include agent names or meta commentary."
    )
    timely_context = f"{tavily_block}\n" if tavily_block else ""
    user = (
        f"Target agent (route HERE):\n{agent.routing_card()}\n\n"
        "Adjacent agents (generate HARD NEGATIVES — utterances that sound related "
        "but must NOT match these):\n"
        f"{peer_cards or '(none)'}\n\n"
        f"{timely_context}"
        f"Generate exactly {count} user queries that should be routed ONLY to the target agent.\n"
        "Include ~20% hard negatives: phrasing that could confuse adjacent agents "
        "but still belongs to the target.\n"
    )
    data = nebius.chat_json(
        system=system,
        user=user,
        model=settings.centri_llm_model_synthesis,
        temperature=0.7,
        max_tokens=4096,
    )
    queries = data.get("queries") or []
    cleaned = [str(q).strip() for q in queries if str(q).strip()]
    return cleaned[:count]


def load_or_build_query_bank(
    agent: AgentRecord,
    catalog: AgentCatalog,
    nebius: NebiusClient | None,
    tavily: TavilyClient,
    settings: Settings,
    cached: dict[str, list[str]],
) -> list[str]:
    if agent.agent_id in cached:
        return cached[agent.agent_id]
    seeds = bootstrap_seed_queries(agent)
    target = settings.centri_queries_per_agent
    if nebius is None or not settings.nebius_api_key:
        return list(dict.fromkeys(seeds))[:target]

    need = max(0, target - len(seeds))
    generated: list[str] = []
    if need > 0:
        generated = generate_synthetic_queries(agent, catalog, nebius, tavily, settings, need)
    all_q = list(dict.fromkeys(seeds + generated))
    return all_q[:target]


def build_full_query_bank(
    catalog: AgentCatalog,
    nebius: NebiusClient | None,
    tavily: TavilyClient,
    settings: Settings,
    cached_path: Path,
) -> dict[str, list[str]]:
    metadata = {
        "catalog_fingerprint": catalog.fingerprint(),
        "embedding_model": settings.centri_embedding_model,
        "synthesis_model": settings.centri_llm_model_synthesis,
        "queries_per_agent": settings.centri_queries_per_agent,
    }
    cached: dict[str, list[str]] = {}
    if cached_path.exists():
        payload = json.loads(cached_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("metadata") == metadata:
            cached = payload.get("queries") or {}
    bank: dict[str, list[str]] = {}
    for agent in catalog.agents:
        bank[agent.agent_id] = load_or_build_query_bank(
            agent, catalog, nebius, tavily, settings, cached
        )
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    cached_path.write_text(
        json.dumps({"metadata": metadata, "queries": bank}, indent=2),
        encoding="utf-8",
    )
    return bank
