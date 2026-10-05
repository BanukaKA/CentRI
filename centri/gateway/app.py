from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from centri.agents.executor import AgentExecutor
from centri.clients.nebius import NebiusClient
from centri.config import Settings, get_settings
from centri.feedback.shadow_log import ShadowLogger
from centri.gateway.auth import Principal, admin_principal, authenticated_principal
from centri.index.store import VectorIndex
from centri.registry import agent_catalog_entry, load_catalog
from centri.routing.pipeline import CentRIRouter


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    approval_granted: bool = False


class RouteRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User utterance to route to an agent")


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
    executor: AgentExecutor
    shadow: ShadowLogger


def _build_state() -> AppState:
    settings = get_settings()
    catalog = load_catalog(settings.centri_agent_catalog)
    index = VectorIndex(settings)
    index.load(
        expected_manifest={
            "catalog_fingerprint": catalog.fingerprint(),
            "embedding_model": settings.centri_embedding_model,
        }
    )
    nebius = NebiusClient(settings)
    router = CentRIRouter(settings, catalog, index, nebius)
    executor = AgentExecutor(catalog, settings)
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
    try:
        yield
    finally:
        await app.state.centri.executor.close()


app = FastAPI(
    title="CentRI",
    description="Central Routing Intelligence — semantic gateway for agent swarms",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    st: AppState | None = getattr(app.state, "centri", None)
    return {
        "status": "ok",
        "service": "centri",
        "index": {
            "loaded": st is not None and st.index.index is not None,
            "type": st.index.index_type if st else None,
            "vectors": len(st.index.records) if st else 0,
            "version": st.index.version if st else 0,
        },
    }


@app.get("/agents")
def list_agents(_: Principal = Depends(authenticated_principal)) -> dict[str, Any]:
    st: AppState = app.state.centri
    return {
        "count": len(st.catalog.agents),
        "agents": [
            {**agent_catalog_entry(a), "domain": a.domain}
            for a in st.catalog.agents
        ],
    }


@app.get("/catalog")
def catalog(_: Principal = Depends(authenticated_principal)) -> dict[str, Any]:
    """All agents from the configured catalog JSON: id, name(s), and description."""
    st: AppState = app.state.centri
    return {
        "count": len(st.catalog.agents),
        "agents": [agent_catalog_entry(a) for a in st.catalog.agents],
    }


@app.post("/route")
def route(
    body: RouteRequest,
    request: Request,
    _: Principal = Depends(authenticated_principal),
) -> dict[str, Any]:
    """Return which agent(s) to call for a query — routing only, no agent execution."""
    st: AppState = app.state.centri
    try:
        routing = st.router.route(body.query)
    except Exception as exc:
        st.shadow.log(
            {
                "endpoint": "/route",
                "request_id": request.state.request_id,
                "error_type": type(exc).__name__,
            }
        )
        raise HTTPException(status_code=503, detail="Routing service unavailable") from exc

    routes = [
        {
            "agent_id": d.agent_id,
            "agent_name": d.agent_name,
            "query": d.intent_shard,
            "abstained": d.abstained,
            "confidence": d.confidence,
            "abstention_reason": d.abstention_reason,
            "candidates": d.candidates,
        }
        for d in routing.decisions
    ]
    for d in routing.decisions:
        st.shadow.log(
            {
                "endpoint": "/route",
                "prompt": body.query,
                "shard": d.intent_shard,
                "routed_agent_id": d.agent_id,
                "confidence": d.confidence,
                "compound": routing.compound,
                "request_id": request.state.request_id,
                "abstained": d.abstained,
            }
        )

    if not routing.compound and len(routes) == 1:
        return {
            "agent_id": routes[0]["agent_id"],
            "agent_name": routes[0]["agent_name"],
            "compound": False,
            "abstained": routes[0]["abstained"],
            "confidence": routes[0]["confidence"],
            "abstention_reason": routes[0]["abstention_reason"],
            "candidates": routes[0]["candidates"],
        }

    return {
        "compound": routing.compound,
        "routes": routes,
    }


@app.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    _: Principal = Depends(authenticated_principal),
) -> dict[str, Any]:
    st: AppState = app.state.centri
    try:
        routing = st.router.route(body.prompt)
    except Exception as exc:
        st.shadow.log(
            {
                "endpoint": "/chat",
                "request_id": request.state.request_id,
                "error_type": type(exc).__name__,
            }
        )
        raise HTTPException(status_code=503, detail="Routing service unavailable") from exc

    history = [{"role": m.role, "content": m.content} for m in body.history]
    async def execute_decision(decision):
        if decision.abstained:
            return {
                "status": "abstained",
                "message": "CentRI could not route this intent with sufficient confidence.",
                "routable": False,
            }
        return await st.executor.execute(
            decision,
            body.prompt,
            history,
            approval_granted=body.approval_granted,
        )

    results = await asyncio.gather(
        *(execute_decision(decision) for decision in routing.decisions),
        return_exceptions=True,
    )
    outputs = []
    for decision, result in zip(routing.decisions, results, strict=True):
        if isinstance(result, Exception):
            result = {
                "status": "error",
                "message": "Agent execution failed",
                "routable": True,
                "error_type": type(result).__name__,
            }
        outputs.append(
            {
                "routing": {
                    "agent_id": decision.agent_id,
                    "agent_name": decision.agent_name,
                    "confidence": decision.confidence,
                    "rationale": decision.rationale,
                    "intent_shard": decision.intent_shard,
                    "vector_hits": decision.vector_hits,
                    "candidates": decision.candidates,
                    "similarity": decision.similarity,
                    "margin": decision.margin,
                    "abstained": decision.abstained,
                    "abstention_reason": decision.abstention_reason,
                },
                "agent_response": result,
            }
        )
        st.shadow.log(
            {
                "endpoint": "/chat",
                "request_id": request.state.request_id,
                "prompt": body.prompt,
                "shard": decision.intent_shard,
                "routed_agent_id": decision.agent_id or "abstained",
                "confidence": decision.confidence,
                "compound": routing.compound,
                "agent_refused": not result.get("routable", True),
                "status": result.get("status"),
            }
        )

    synthesis = None
    if routing.compound and st.settings.nebius_api_key:
        successful = [
            output["agent_response"]
            for output in outputs
            if output["agent_response"].get("status") in {"ok", "simulated"}
        ]
        if successful:
            synthesis = await asyncio.to_thread(
                st.nebius.chat_text,
                "Synthesize the independent agent results into a concise answer. "
                "Do not invent facts and preserve uncertainty.",
                json.dumps(
                    {"original_prompt": body.prompt, "results": successful},
                    ensure_ascii=False,
                ),
                temperature=0.2,
                max_tokens=1200,
            )

    return {
        "compound": routing.compound,
        "results": outputs,
        "synthesis": synthesis,
    }


@app.post("/feedback/routing")
def routing_feedback(
    body: FeedbackRequest,
    request: Request,
    _: Principal = Depends(admin_principal),
) -> dict[str, Any]:
    """Implicit/explicit feedback — append corrected vectors to the index."""
    st: AppState = app.state.centri
    target = body.correct_agent_id
    if target and st.catalog.by_id(target) is None:
        raise HTTPException(status_code=400, detail="Unknown correct_agent_id")
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
                "request_id": request.state.request_id,
            }
        )
        return {"status": "corrected", "agent_id": target}
    st.shadow.log(
        {
            "type": "feedback",
            "query": body.query,
            "routed_agent_id": body.routed_agent_id,
            "agent_refused": body.agent_refused,
            "request_id": request.state.request_id,
        }
    )
    return {"status": "logged"}


def main() -> None:
    import uvicorn

    uvicorn.run("centri.gateway.app:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
