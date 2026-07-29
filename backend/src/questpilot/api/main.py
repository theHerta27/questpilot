from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from time import monotonic
from typing import Annotated
from uuid import uuid4

import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from questpilot.agent_graph import PlanningGraph
from questpilot.agent_runtime import AgentRuntime
from questpilot.config import get_settings
from questpilot.database import SessionLocal, create_all, get_session
from questpilot.domain_tools import build_tool_registry
from questpilot.harness.context import ExecutionContext
from questpilot.harness.events import CompositeEventSink, InMemoryEventSink
from questpilot.harness.gateway import FakeModel, OpenAICompatibleGateway
from questpilot.harness.persistence import CheckpointStore, DatabaseEventSink
from questpilot.models import AgentRun
from questpilot.observability import AppMetrics, configure_telemetry, tracer
from questpilot.planner import LocalPlanner
from questpilot.rag import MooncellIndex
from questpilot.replay import ReplayService
from questpilot.repositories import GameRepository
from questpilot.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    CharacterSummary,
    InventoryItemView,
    InventoryReplaceRequest,
    MaterialGapRequest,
    MaterialGapResult,
    PlanRequest,
    PlanResult,
    RagAnswer,
    SkillCostItem,
)
from questpilot.services import GameService

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = structlog.get_logger()
app = FastAPI(
    title="QuestPilot API",
    version="0.1.0",
    description="可验证的复杂养成游戏规划 Agent",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
memory_event_sink = InMemoryEventSink()
database_event_sink = DatabaseEventSink(SessionLocal)
event_sink = CompositeEventSink(memory_event_sink, database_event_sink)
SessionDep = Annotated[Session, Depends(get_session)]
metrics = AppMetrics()


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started = monotonic()
    if (
        settings.app_api_key
        and request.url.path.startswith("/api/")
        and request.headers.get("x-api-key") != settings.app_api_key
    ):
        metrics.observe(request.url.path, 401, (monotonic() - started) * 1000)
        return JSONResponse(status_code=401, content={"detail": "invalid API key"})
    with tracer().start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("request.id", request_id)
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("request_failed", request_id=request_id, path=request.url.path)
            span.record_exception(exc)
            metrics.observe(request.url.path, 500, (monotonic() - started) * 1000)
            raise
    metrics.observe(request.url.path, response.status_code, (monotonic() - started) * 1000)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(KeyError)
async def key_error_handler(_: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def service(session: Session) -> GameService:
    return GameService(GameRepository(session))


def begin_run(
    session: Session,
    context: ExecutionContext,
    *,
    user_id: str,
    input_json: dict,
    model_name: str,
    prompt_id: str,
) -> AgentRun:
    run = AgentRun(
        id=context.run_id,
        request_id=context.request_id,
        trace_id=context.trace_id,
        user_id=user_id,
        input_json=input_json,
        model_name=model_name,
        prompt_id=prompt_id,
        prompt_version="1.0.0",
    )
    session.add(run)
    session.commit()
    return run


def finish_run(session: Session, run: AgentRun, output: dict | None, status: str) -> None:
    run.status = status
    run.output_json = output
    run.finished_at = datetime.now(UTC)
    session.commit()


@app.on_event("startup")
def startup() -> None:
    configure_telemetry()
    create_all()
    logger.info("questpilot_started", environment=settings.app_env)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "questpilot-api", "version": "0.1.0"}


@app.get("/metrics")
def app_metrics() -> dict:
    return metrics.snapshot()


@app.get("/api/v1/system/capabilities")
def capabilities() -> dict:
    return {
        "database": "postgresql" if settings.database_url.startswith("postgresql") else "sqlite",
        "pgvector": settings.pgvector_enabled,
        "redis": bool(settings.redis_url),
        "object_storage": bool(settings.object_storage_endpoint),
        "model_provider": settings.model_provider,
        "authentication": bool(settings.app_api_key),
    }


@app.get("/api/v1/characters", response_model=list[CharacterSummary])
def characters(
    query: Annotated[str, Query(min_length=1)],
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CharacterSummary]:
    return service(session).search_characters(query, limit)


@app.get("/api/v1/characters/{character_id}/skill-costs", response_model=list[SkillCostItem])
def skill_costs(
    character_id: int, session: SessionDep
) -> list[SkillCostItem]:
    character = GameRepository(session).get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="character not found")
    return service(session).skill_costs(character_id)


@app.get("/api/v1/account/inventory", response_model=list[InventoryItemView])
def get_inventory(
    session: SessionDep, user_id: str = "demo"
) -> list[InventoryItemView]:
    return service(session).inventory(user_id)


@app.put("/api/v1/account/inventory", response_model=list[InventoryItemView])
def put_inventory(
    payload: InventoryReplaceRequest, session: SessionDep
) -> list[InventoryItemView]:
    return service(session).update_inventory(payload)


@app.post("/api/v1/calculations/material-gap", response_model=MaterialGapResult)
def material_gap(
    payload: MaterialGapRequest, session: SessionDep
) -> MaterialGapResult:
    return service(session).material_gap(payload)


@app.post("/api/v1/agent/query", response_model=AgentQueryResponse)
async def agent_query(
    payload: AgentQueryRequest, session: SessionDep
) -> AgentQueryResponse:
    gateway = (
        OpenAICompatibleGateway(
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
            model=settings.model_name,
        )
        if settings.model_provider != "fake" and settings.model_api_key
        else FakeModel()
    )
    model_name = settings.model_name if settings.model_provider != "fake" else "fake"
    context = ExecutionContext(
        user_id=payload.user_id,
        locale=payload.locale,
        model_config={"provider": settings.model_provider, "model": model_name},
        event_sink=event_sink,
    )
    run = begin_run(
        session,
        context,
        user_id=payload.user_id,
        input_json=payload.model_dump(mode="json"),
        model_name=model_name,
        prompt_id="agent.system",
    )
    runtime = AgentRuntime(gateway, build_tool_registry(service(session)))
    try:
        result = await runtime.run(payload.query, context)
    except Exception:
        finish_run(session, run, None, "failed")
        raise
    finish_run(session, run, result.model_dump(mode="json"), "complete")
    return result


@app.post("/api/v1/plans", response_model=PlanResult)
def create_plan(
    payload: PlanRequest, session: SessionDep
) -> PlanResult:
    context = ExecutionContext(
        user_id=payload.user_id,
        model_config={"provider": "deterministic", "model": "local-planner"},
        event_sink=event_sink,
    )
    run = begin_run(
        session,
        context,
        user_id=payload.user_id,
        input_json=payload.model_dump(mode="json"),
        model_name="local-planner",
        prompt_id="planner.workflow",
    )
    planner = LocalPlanner(session, service(session))
    graph = PlanningGraph(planner, service(session), CheckpointStore(session))
    try:
        result = graph.invoke(payload, context)
    except Exception:
        finish_run(session, run, None, "failed")
        raise
    finish_run(session, run, result.model_dump(mode="json"), "complete")
    return result


@app.get("/api/v1/plans/{plan_id}", response_model=PlanResult)
def get_plan(plan_id: str, session: SessionDep) -> PlanResult:
    result = LocalPlanner(session, service(session)).get(plan_id)
    if not result:
        raise HTTPException(status_code=404, detail="plan not found")
    return result


@app.get("/api/v1/tasks/{run_id}/events")
async def task_events(run_id: str) -> StreamingResponse:
    async def stream():
        events = event_sink.events_for(run_id)
        if not events:
            events = database_event_sink.events_for(run_id)
        for item in events:
            yield f"event: {item.event_type}\ndata: {item.model_dump_json()}\n\n"
            await asyncio.sleep(0)
        yield 'event: stream.closed\ndata: {"status":"complete"}\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/v1/traces/{run_id}")
def trace_detail(run_id: str) -> dict:
    events = database_event_sink.events_for(run_id)
    if not events:
        raise HTTPException(status_code=404, detail="trace not found")
    return {"run_id": run_id, "events": [item.model_dump(mode="json") for item in events]}


@app.get("/api/v1/replays/{run_id}")
def replay_bundle(run_id: str, session: SessionDep) -> dict:
    return ReplayService(session).bundle(run_id)


@app.get("/api/v1/knowledge/query", response_model=RagAnswer)
def knowledge_query(
    query: Annotated[str, Query(min_length=1)], session: SessionDep
) -> RagAnswer:
    return MooncellIndex(session).answer(query)


def run() -> None:
    uvicorn.run("questpilot.api.main:app", host="127.0.0.1", port=8000, reload=True)
