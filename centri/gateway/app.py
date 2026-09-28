from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from centri.agents.executor import StubAgentExecutor
from centri.clients.nebius import NebiusClient
from centri.config import Settings, get_settings
from centri.feedback.shadow_log import ShadowLogger
from centri.index.store import VectorIndex
from centri.registry import load_catalog
from centri.routing.pipeline import CentRIRouter


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    query: str
    routed_agent_id: str
    correct_agent_id: str | None = None
    agent_refused: bool = False


class AppState:
    settings: Settings
    catalog: Any
    index: VectorIndex
    nebius: NebiusClient
    router: CentRIRouter
    executor: StubAgentExecutor
    shadow: ShadowLogger


def _build_state() -> AppState:
    settings = get_settings()
    catalog = load_catalog(settings.centri_agent_catalog)
    index = VectorIndex(settings)
    index.load()
    nebius = NebiusClient(settings)
    router = CentRIRouter(settings, catalog, index, nebius)
    executor = StubAgentExecutor(catalog)
    shadow = ShadowLogger(settings)
    state = AppState()
    state.settings = settings
    state.catalog = catalog
    state.index = index
    state.nebius = nebius
    state.router = router
    state.executor = executor
    state.shadow = shadow
    return state


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.centri = _build_state()
    yield


app = FastAPI(
    title="CentRI",
    description="Central Routing Intelligence — semantic gateway for agent swarms",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "centri"}


@app.get("/agents")
def list_agents() -> dict[str, Any]:
    st: AppState = app.state.centri
    return {
        "count": len(st.catalog.agents),
        "agents": [
            {"agent_id": a.agent_id, "name": a.name, "domain": a.domain}
            for a in st.catalog.agents
        ],
    }


@app.post("/chat")
def chat(body: ChatRequest) -> dict[str, Any]:
    st: AppState = app.state.centri
    try:
        routing = st.router.route(body.prompt)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    history = [{"role": m.role, "content": m.content} for m in body.history]
    outputs = []
    for decision in routing.decisions:
        result = st.executor.execute(decision, body.prompt, history)
        outputs.append(
            {
                "routing": {
                    "agent_id": decision.agent_id,
                    "agent_name": decision.agent_name,
                    "confidence": decision.confidence,
                    "rationale": decision.rationale,
                    "intent_shard": decision.intent_shard,
                    "vector_hits": decision.vector_hits,
                },
                "agent_response": result,
            }
        )
        st.shadow.log(
            {
                "prompt": body.prompt,
                "shard": decision.intent_shard,
                "routed_agent_id": decision.agent_id,
                "confidence": decision.confidence,
                "compound": routing.compound,
                "top_vector_hits": decision.vector_hits,
                "agent_refused": not result.get("routable", True),
            }
        )

    return {
        "compound": routing.compound,
        "results": outputs,
    }


@app.post("/feedback/routing")
def routing_feedback(body: FeedbackRequest) -> dict[str, Any]:
    """Implicit/explicit feedback — append corrected vectors to the index."""
    st: AppState = app.state.centri
    target = body.correct_agent_id
    if body.agent_refused and not target:
        raise HTTPException(
            status_code=400,
            detail="correct_agent_id required when agent_refused is true",
        )
    if target:
        st.index.append_correction(st.nebius, target, body.query)
        st.shadow.log(
            {
                "type": "correction",
                "query": body.query,
                "wrong_agent_id": body.routed_agent_id,
                "correct_agent_id": target,
            }
        )
        return {"status": "corrected", "agent_id": target}
    st.shadow.log(
        {
            "type": "feedback",
            "query": body.query,
            "routed_agent_id": body.routed_agent_id,
            "agent_refused": body.agent_refused,
        }
    )
    return {"status": "logged"}


def main() -> None:
    import uvicorn

    uvicorn.run("centri.gateway.app:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
