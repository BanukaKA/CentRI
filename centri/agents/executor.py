from __future__ import annotations

from typing import Any

from centri.registry import AgentCatalog, AgentRecord
from centri.routing.pipeline import RouteDecision


class StubAgentExecutor:
    """
    PoC handoff layer — simulates dispatch to each agent's runtime endpoint.
    Replace with HTTP/MCP/function calls per agent in production.
    """

    def __init__(self, catalog: AgentCatalog) -> None:
        self.catalog = catalog

    def execute(
        self,
        decision: RouteDecision,
        user_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        agent = self.catalog.by_id(decision.agent_id)
        if agent is None:
            return {
                "status": "error",
                "message": "I cannot help with that — unknown agent.",
                "routable": False,
            }
        return {
            "status": "ok",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "domain": agent.domain,
            "message": self._stub_response(agent, user_prompt),
            "handoff": {
                "runtime_provider": (agent.raw.get("runtime") or {}).get("provider"),
                "model": (agent.raw.get("runtime") or {}).get("model"),
                "tool_count": len(agent.tools),
            },
            "routable": True,
        }

    def _stub_response(self, agent: AgentRecord, user_prompt: str) -> str:
        return (
            f"[{agent.name}] Received your request. "
            f"In production, this would run the agent workflow with tools and guardrails. "
            f"Prompt preview: {user_prompt[:200]}{'...' if len(user_prompt) > 200 else ''}"
        )
