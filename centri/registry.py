from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AgentRecord(BaseModel):
    agent_id: str
    name: str
    description: str
    domain: str = ""
    tags: list[str] = Field(default_factory=list)
    routing: dict[str, Any] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)

    def routing_card(self) -> str:
        """Compact schema for re-rank / disambiguation (no full system prompt)."""
        intents = self.routing.get("intent_labels") or []
        keywords = self.routing.get("keywords") or []
        examples = self.routing.get("example_queries") or []
        exclusions = self.routing.get("exclusions") or []
        tool_names = [t.get("name") or t.get("tool_id", "") for t in self.tools[:12]]
        lines = [
            f"agent_id: {self.agent_id}",
            f"name: {self.name}",
            f"domain: {self.domain}",
            f"description: {self.description}",
            f"intent_labels: {', '.join(intents)}",
            f"keywords: {', '.join(keywords[:20])}",
            f"tools: {', '.join(filter(None, tool_names))}",
            f"exclusions: {', '.join(exclusions)}",
            "example_queries:",
        ]
        for ex in examples[:6]:
            lines.append(f"  - {ex}")
        return "\n".join(lines)


class AgentCatalog(BaseModel):
    agents: list[AgentRecord]

    def by_id(self, agent_id: str) -> AgentRecord | None:
        for a in self.agents:
            if a.agent_id == agent_id:
                return a
        return None


def agent_catalog_entry(agent: AgentRecord) -> dict[str, str]:
    """Public catalog shape: id, names, description from the loaded dataset."""
    entry: dict[str, str] = {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description or "",
    }
    display_name = agent.raw.get("display_name")
    if isinstance(display_name, str) and display_name.strip():
        entry["display_name"] = display_name.strip()
    return entry


def load_catalog(path: Path) -> AgentCatalog:
    data = json.loads(path.read_text(encoding="utf-8"))
    agents: list[AgentRecord] = []
    for item in data.get("agents", []):
        agents.append(
            AgentRecord(
                agent_id=item["agent_id"],
                name=item.get("name", item["agent_id"]),
                description=item.get("description", ""),
                domain=item.get("domain", ""),
                tags=item.get("tags") or [],
                routing=item.get("routing") or {},
                tools=item.get("tools") or [],
                knowledge=item.get("knowledge") or {},
                raw=item,
            )
        )
    return AgentCatalog(agents=agents)


def adjacent_agents(agent: AgentRecord, catalog: AgentCatalog, k: int = 2) -> list[AgentRecord]:
    """Pick agents with overlapping routing keywords (contrastive hard-negative peers)."""
    mine = set(agent.routing.get("keywords") or [])
    mine |= set(agent.tags)
    scored: list[tuple[float, AgentRecord]] = []
    for other in catalog.agents:
        if other.agent_id == agent.agent_id:
            continue
        theirs = set(other.routing.get("keywords") or [])
        theirs |= set(other.tags)
        if not mine and not theirs:
            overlap = 0.0
        else:
            overlap = len(mine & theirs) / max(len(mine | theirs), 1)
        if agent.domain and other.domain == agent.domain:
            overlap += 0.25
        scored.append((overlap, other))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:k]]
