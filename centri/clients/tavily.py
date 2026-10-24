from __future__ import annotations

from typing import Any

import httpx

from centri.config import Settings
from centri.registry import AgentRecord


class TavilyClient:
    """Thin wrapper around Tavily search for grounding synthetic query generation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.tavily_api_key)

    def should_search(self, query: str, agent: AgentRecord | None = None) -> bool:
        """Decide whether a live runtime search is relevant for this request."""
        if not self.enabled:
            return False
        freshness_required = False
        if agent is not None:
            for source in (agent.knowledge or {}).get("sources") or []:
                sla = source.get("freshness_sla_days")
                if isinstance(sla, int) and sla <= 30:
                    freshness_required = True
                    break
        current_markers = (
            "latest",
            "recent",
            "today",
            "current",
            "news",
            "breaking",
            "as of",
            "this week",
            "this month",
        )
        return freshness_required or any(marker in query.lower() for marker in current_markers)

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query[:400],
            "max_results": max_results,
            "search_depth": "basic",
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("results") or []

    def runtime_search(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Make the optional live Tavily call used by the /chat runtime path."""
        if not self.enabled:
            return {
                "status": "disabled",
                "query": query,
                "results": [],
            }
        try:
            results = self.search(query, max_results=max_results)
            return {
                "status": "ok",
                "query": query,
                "results": [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": (result.get("content") or "")[:1200],
                    }
                    for result in results
                ],
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "status": "error",
                "query": query,
                "results": [],
                "error_type": type(exc).__name__,
            }
