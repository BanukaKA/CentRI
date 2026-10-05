from __future__ import annotations

from typing import Any

from centri.registry import AgentRecord


def ordered_workflow_steps(agent: AgentRecord) -> list[dict[str, Any]]:
    """Topologically order catalog workflow steps for an HTTP runtime."""
    workflow = agent.raw.get("workflow") or {}
    steps = workflow.get("steps") or []
    by_id = {str(step.get("step_id")): step for step in steps if step.get("step_id")}
    dependencies = {
        step_id: {
            str(dep)
            for dep in (step.get("depends_on") or [])
            if str(dep) in by_id
        }
        for step_id, step in by_id.items()
    }
    ordered: list[dict[str, Any]] = []
    while dependencies:
        ready = sorted(step_id for step_id, deps in dependencies.items() if not deps)
        if not ready:
            raise ValueError(f"Workflow dependency cycle for agent {agent.agent_id}")
        for step_id in ready:
            ordered.append(by_id[step_id])
            dependencies.pop(step_id)
        for deps in dependencies.values():
            deps.difference_update(ready)
    return ordered
