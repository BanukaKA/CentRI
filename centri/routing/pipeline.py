from __future__ import annotations

from dataclasses import dataclass, field
import re

from centri.clients.nebius import NebiusClient
from centri.config import Settings
from centri.index.store import VectorIndex
from centri.registry import AgentCatalog
from centri.routing.intent_split import split_intents
from centri.routing.rerank import rerank_agents


@dataclass
class RouteDecision:
    agent_id: str | None
    agent_name: str | None
    confidence: float
    rationale: str
    intent_shard: str
    vector_hits: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    similarity: float | None = None
    margin: float | None = None
    abstained: bool = False
    abstention_reason: str | None = None


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

    def _aggregate_agent_scores(
        self, hits: list[tuple[int, float]]
    ) -> list[tuple[str, float, list[dict], float]]:
        """k-NN vote + max similarity per agent."""
        per_agent_scores: dict[str, list[float]] = {}
        per_agent_hits: dict[str, list[dict]] = {}
        for idx, score in hits:
            rec = self.index.records[idx]
            per_agent_scores.setdefault(rec.agent_id, []).append(score)
            per_agent_hits.setdefault(rec.agent_id, []).append(
                {"query": rec.query_text, "score": score, "source": rec.source}
            )
        ranked: list[tuple[str, float, list[dict], float]] = []
        for agent_id, scores in per_agent_scores.items():
            vote = len(scores)
            max_sim = max(scores)
            combined = max_sim + 0.02 * vote
            ranked.append((agent_id, combined, per_agent_hits[agent_id], max_sim))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    @staticmethod
    def _normalized(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _is_excluded(self, prompt: str, agent_id: str) -> bool:
        agent = self.catalog.by_id(agent_id)
        if agent is None:
            return True
        normalized_prompt = self._normalized(prompt)
        for exclusion in agent.routing.get("exclusions") or []:
            terms = self._normalized(str(exclusion)).split()
            if terms and all(term in normalized_prompt.split() for term in terms):
                return True
        return False

    def route_shard(self, prompt: str) -> RouteDecision:
        if self.nebius is None:
            raise RuntimeError("NEBIUS_API_KEY required for runtime embedding")
        q_vec = self.nebius.embed_one(prompt)
        hits = self.index.search(q_vec, self.settings.centri_top_k_vectors)
        ranked = self._aggregate_agent_scores(hits)
        if not ranked:
            raise RuntimeError("Vector index returned no hits")

        filtered = [row for row in ranked if not self._is_excluded(prompt, row[0])]
        if not filtered:
            return RouteDecision(
                agent_id=None,
                agent_name=None,
                confidence=0.0,
                rationale="all_candidates_excluded_by_catalog_policy",
                intent_shard=prompt,
                abstained=True,
                abstention_reason="catalog_exclusion",
            )

        top_agent_ids = [
            a for a, _, _, _ in filtered[: self.settings.centri_top_k_agents_rerank]
        ]
        candidates = [self.catalog.by_id(a) for a in top_agent_ids]
        candidates = [c for c in candidates if c is not None]

        agent_id, conf, rationale = rerank_agents(prompt, candidates, self.nebius, self.settings)
        agent = self.catalog.by_id(agent_id)
        name = agent.name if agent else agent_id
        chosen_row = next((row for row in filtered if row[0] == agent_id), filtered[0])
        best_hits = chosen_row[2]
        top_similarity = filtered[0][3]
        margin = (
            filtered[0][1] - filtered[1][1]
            if len(filtered) > 1
            else filtered[0][1]
        )
        catalog_threshold = float((agent.routing or {}).get("confidence_threshold", 0.0)) if agent else 0.0
        abstention_reason = None
        if top_similarity < self.settings.centri_route_min_similarity:
            abstention_reason = "vector_similarity_below_threshold"
        elif conf < max(0.4, catalog_threshold):
            abstention_reason = "reranker_confidence_below_threshold"
        elif margin < self.settings.centri_route_min_margin and conf < 0.75:
            abstention_reason = "candidate_margin_too_small"
        if abstention_reason:
            return RouteDecision(
                agent_id=None,
                agent_name=None,
                confidence=conf,
                rationale=rationale,
                intent_shard=prompt,
                vector_hits=best_hits[:5],
                candidates=[
                    {"agent_id": aid, "score": score, "similarity": similarity}
                    for aid, score, _, similarity in filtered[: self.settings.centri_top_k_agents_rerank]
                ],
                similarity=top_similarity,
                margin=margin,
                abstained=True,
                abstention_reason=abstention_reason,
            )
        return RouteDecision(
            agent_id=agent_id,
            agent_name=name,
            confidence=conf,
            rationale=rationale,
            intent_shard=prompt,
            vector_hits=best_hits[:5],
            candidates=[
                {"agent_id": aid, "score": score, "similarity": similarity}
                for aid, score, _, similarity in filtered[: self.settings.centri_top_k_agents_rerank]
            ],
            similarity=top_similarity,
            margin=margin,
        )

    def route(self, prompt: str) -> RoutingResult:
        shards = split_intents(prompt, self.nebius, self.settings)
        decisions = [self.route_shard(s) for s in shards]
        return RoutingResult(decisions=decisions, compound=len(decisions) > 1)
