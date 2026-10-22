from __future__ import annotations

from centri.clients.nebius import NebiusClient
from centri.config import Settings


def split_intents(prompt: str, nebius: NebiusClient | None, settings: Settings) -> list[str]:
    """
    Multi-intent sharding: return one or more atomic user intents.
    Uses a lightweight LLM when available; otherwise heuristics.
    """
    if not _looks_compound(prompt):
        return [prompt]
    if nebius is None or not settings.nebius_api_key:
        return _heuristic_split(prompt, settings.centri_max_intent_shards)

    system = (
        "Detect compound user requests. Output JSON: "
        '{"intents": ["..."], "compound": true|false}. '
        "If a single coherent goal, return one intent. "
        "Split only when distinct agents would likely handle separate parts."
    )
    try:
        data = nebius.chat_json(
            system=system,
            user=prompt,
            model=settings.centri_llm_model,
            temperature=0.0,
            max_tokens=512,
        )
        intents = [
            str(i).strip()
            for i in (data.get("intents") or [])[: settings.centri_max_intent_shards]
            if str(i).strip()
        ]
        if intents:
            return intents
    except Exception:
        pass
    return _heuristic_split(prompt, settings.centri_max_intent_shards)


def _heuristic_split(prompt: str, max_shards: int = 3) -> list[str]:
    lowered = prompt.lower()
    markers = [" and also ", " and then ", "; ", " — ", " - "]
    for m in markers:
        if m in lowered and len(prompt) > 40:
            parts = [p.strip() for p in prompt.split(m) if p.strip()]
            if len(parts) >= 2:
                return parts[:max_shards]
    return [prompt]


def _looks_compound(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(
        marker in lowered
        for marker in (" and also ", " and then ", "; ", " — ", " plus ", " - ")
    )
