from __future__ import annotations

from typing import Any

import httpx

from centri.config import Settings


class TavilyClient:
    """Thin wrapper around Tavily search for grounding synthetic query generation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.tavily_api_key)

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
