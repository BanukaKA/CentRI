from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from centri.clients.nebius import NebiusClient
from centri.config import Settings
from centri.index.store import VectorIndex
from centri.registry import AgentCatalog
from centri.routing.intent_split import split_intents
from centri.routing.rerank import rerank_agents


@dataclass
class RouteDecision:
    agent_id: str
    agent_name: str
    confidence: float
    rationale: str
    intent_shard: str
    vector_hits: list[dict] = field(default_factory=list)


@dataclass
class RoutingResult:
    decisions: list[RouteDecision]
    compound: bool


class CentRIRouter:
    def __init__(
        self,
        settings: Settings,
        catalog: AgentCatalog,
        index: VectorIndex,
        nebius: NebiusClient | None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.index = index
        self.nebius = nebius

    def _aggregate_agent_scores(self, hits: list[tuple[int, float]]) -> list[tuple[str, float, list[dict]]]:
        """k-NN vote + max similarity per agent."""
        per_agent_scores: dict[str, list[float]] = {}
        per_agent_hits: dict[str, list[dict]] = {}
        for idx, score in hits:
            rec = self.index.records[idx]
            per_agent_scores.setdefault(rec.agent_id, []).append(score)
            per_agent_hits.setdefault(rec.agent_id, []).append(
                {"query": rec.query_text, "score": score, "source": rec.source}
            )
        ranked: list[tuple[str, float, list[dict]]] = []
        for agent_id, scores in per_agent_scores.items():
            vote = len(scores)
            max_sim = max(scores)
            combined = max_sim + 0.02 * vote
            ranked.append((agent_id, combined, per_agent_hits[agent_id]))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def route_shard(self, prompt: str) -> RouteDecision:
        if self.nebius is None:
            raise RuntimeError("NEBIUS_API_KEY required for runtime embedding")
        q_vec = self.nebius.embed_one(prompt)
        hits = self.index.search(q_vec, self.settings.centri_top_k_vectors)
        ranked = self._aggregate_agent_scores(hits)
        if not ranked:
            raise RuntimeError("Vector index returned no hits")

        top_agent_ids = [a for a, _, _ in ranked[: self.settings.centri_top_k_agents_rerank]]
        candidates = [self.catalog.by_id(a) for a in top_agent_ids]
        candidates = [c for c in candidates if c is not None]

        agent_id, conf, rationale = rerank_agents(prompt, candidates, self.nebius, self.settings)
        agent = self.catalog.by_id(agent_id)
        name = agent.name if agent else agent_id
        best_hits = next((h for aid, _, h in ranked if aid == agent_id), [])
        return RouteDecision(
            agent_id=agent_id,
            agent_name=name,
            confidence=conf,
            rationale=rationale,
            intent_shard=prompt,
            vector_hits=best_hits[:5],
        )

    def route(self, prompt: str) -> RoutingResult:
        shards = split_intents(prompt, self.nebius, self.settings)
        decisions = [self.route_shard(s) for s in shards]
        return RoutingResult(decisions=decisions, compound=len(decisions) > 1)
