from __future__ import annotations

import json
from typing import Any

import httpx

from centri.config import Settings
from centri.agents.orchestrator import ordered_workflow_steps
from centri.registry import AgentCatalog, AgentRecord
from centri.routing.pipeline import RouteDecision


class AgentExecutor:
    """
    Generic HTTP handoff with an explicit sample-catalog mock fallback.

    Runtime endpoint precedence:
      1. agent.raw.runtime.endpoint_url
      2. CENTRI_AGENT_ENDPOINTS_JSON[agent_id]
    """

    def __init__(self, catalog: AgentCatalog, settings: Settings) -> None:
        self.catalog = catalog
        self.settings = settings
        self._client = httpx.AsyncClient(timeout=settings.centri_runtime_timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    def endpoint_for(self, agent: AgentRecord) -> str | None:
        runtime = agent.raw.get("runtime") or {}
        return runtime.get("endpoint_url") or self.settings.agent_endpoints.get(agent.agent_id)

    def requires_human_approval(self, agent: AgentRecord) -> bool:
        review = (agent.raw.get("guardrails") or {}).get("human_review") or {}
        if review.get("required_for"):
            return True
        for tool in agent.tools:
            access_mode = str(tool.get("access_mode", "")).lower()
            if tool.get("approval_required") is True or access_mode in {"write", "admin"}:
                return True
        return False

    async def execute(
        self,
        decision: RouteDecision,
        user_prompt: str,
        history: list[dict[str, str]] | None = None,
        approval_granted: bool = False,
        web_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        agent = self.catalog.by_id(decision.agent_id)
        if agent is None:
            return {
                "status": "error",
                "message": "I cannot help with that — unknown agent.",
                "routable": False,
            }
        if self.requires_human_approval(agent) and not approval_granted:
            return {
                "status": "awaiting_approval",
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "message": "Human approval is required before this agent can perform side effects.",
                "routable": True,
                "approval_required": True,
            }

        endpoint = self.endpoint_for(agent)
        if endpoint:
            try:
                workflow = ordered_workflow_steps(agent)
            except ValueError as exc:
                return {
                    "status": "error",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "message": str(exc),
                    "routable": True,
                }
            payload = {
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "prompt": user_prompt,
                "intent_shard": decision.intent_shard,
                "history": history or [],
                "web_context": web_context or [],
                "routing": {
                    "confidence": decision.confidence,
                    "rationale": decision.rationale,
                },
                "workflow": workflow,
                "guardrails": agent.raw.get("guardrails") or {},
            }
            try:
                response = await self._client.post(endpoint, json=payload)
                response.raise_for_status()
                try:
                    body: Any = response.json()
                except json.JSONDecodeError:
                    body = {"message": response.text}
                return {
                    "status": "ok",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "runtime": "http",
                    "response": body,
                    "routable": True,
                }
            except (httpx.HTTPError, ValueError) as exc:
                return {
                    "status": "error",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "runtime": "http",
                    "message": f"Agent endpoint failed: {type(exc).__name__}",
                    "routable": True,
                }

        if not self.settings.centri_mock_execution:
            return {
                "status": "unavailable",
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "message": "No runtime endpoint is configured for this agent.",
                "routable": True,
            }
        return {
            "status": "simulated",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "domain": agent.domain,
            "message": (
                f"[{agent.name}] Simulated handoff. Configure an endpoint in "
                "CENTRI_AGENT_ENDPOINTS_JSON for real execution."
            ),
            "web_context_items": len(web_context or []),
            "handoff": {
                "runtime_provider": (agent.raw.get("runtime") or {}).get("provider"),
                "model": (agent.raw.get("runtime") or {}).get("model"),
                "tool_count": len(agent.tools),
                "workflow_steps": len((agent.raw.get("workflow") or {}).get("steps") or []),
            },
            "routable": True,
        }


StubAgentExecutor = AgentExecutor
