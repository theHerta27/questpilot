from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from questpilot.harness.events import ExecutionEvent
from questpilot.models import AgentCheckpoint, ExecutionEventRow


class DatabaseEventSink:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def emit(self, event: ExecutionEvent) -> None:
        with self.session_factory() as session:
            session.add(ExecutionEventRow(**event.model_dump()))
            session.commit()

    def events_for(self, run_id: str) -> list[ExecutionEvent]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(ExecutionEventRow)
                .where(ExecutionEventRow.run_id == run_id)
                .order_by(ExecutionEventRow.sequence)
            )
            return [
                ExecutionEvent(
                    event_id=row.event_id,
                    run_id=row.run_id,
                    sequence=row.sequence,
                    event_type=row.event_type,
                    component=row.component,
                    status=row.status,
                    started_at=row.started_at,
                    finished_at=row.finished_at,
                    payload_summary=row.payload_summary,
                    error=row.error,
                    usage=row.usage,
                )
                for row in rows
            ]


class CheckpointStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, run_id: str, node_name: str, state: dict) -> AgentCheckpoint:
        latest = self.session.scalar(
            select(AgentCheckpoint)
            .where(
                AgentCheckpoint.run_id == run_id,
                AgentCheckpoint.node_name == node_name,
            )
            .order_by(AgentCheckpoint.version.desc())
        )
        checkpoint = AgentCheckpoint(
            run_id=run_id,
            node_name=node_name,
            version=(latest.version + 1 if latest else 1),
            state_json=state,
        )
        self.session.add(checkpoint)
        self.session.commit()
        return checkpoint

    def latest(self, run_id: str, node_name: str | None = None) -> AgentCheckpoint | None:
        statement = select(AgentCheckpoint).where(AgentCheckpoint.run_id == run_id)
        if node_name:
            statement = statement.where(AgentCheckpoint.node_name == node_name)
        return self.session.scalar(
            statement.order_by(AgentCheckpoint.created_at.desc(), AgentCheckpoint.version.desc())
        )
