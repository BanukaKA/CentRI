from __future__ import annotations

from centri.clients.nebius import NebiusClient
from centri.config import Settings
from centri.registry import AgentRecord


def rerank_agents(
    prompt: str,
    candidates: list[AgentRecord],
    nebius: NebiusClient | None,
    settings: Settings,
) -> tuple[str, float, str]:
    """
    Stage-2 micro-LLM disambiguation among Top-K agent schemas.
    Returns (agent_id, confidence, rationale).
    """
    if not candidates:
        raise ValueError("No candidates for re-rank")
    if len(candidates) == 1:
        return candidates[0].agent_id, 0.85, "single_candidate"

    if nebius is None or not settings.nebius_api_key:
        return candidates[0].agent_id, 0.6, "vector_only_no_llm"

    cards = "\n\n---\n\n".join(c.routing_card() for c in candidates)
    system = (
        "You are CentRI stage-2 router. Pick exactly one agent_id from the candidates. "
        'Output JSON: {"agent_id": "...", "confidence": 0.0-1.0, "rationale": "..."}'
    )
    user = f"User prompt:\n{prompt}\n\nCandidate agents:\n{cards}"
    try:
        data = nebius.chat_json(
            system=system,
            user=user,
            model=settings.centri_llm_model,
            temperature=0.0,
            max_tokens=256,
        )
        chosen = data.get("agent_id")
        conf = float(data.get("confidence", 0.75))
        rationale = str(data.get("rationale", ""))
        valid = {c.agent_id for c in candidates}
        if chosen in valid:
            return chosen, conf, rationale
    except Exception:
        pass
    return candidates[0].agent_id, 0.55, "rerank_fallback_first_candidate"
