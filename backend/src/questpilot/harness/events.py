from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    sequence: int
    event_type: str
    component: str
    status: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class EventSink(Protocol):
    def emit(self, event: ExecutionEvent) -> None: ...

    def events_for(self, run_id: str) -> list[ExecutionEvent]: ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self._events: list[ExecutionEvent] = []
        self._lock = Lock()

    def emit(self, event: ExecutionEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events_for(self, run_id: str) -> list[ExecutionEvent]:
        with self._lock:
            return sorted(
                (event for event in self._events if event.run_id == run_id),
                key=lambda event: event.sequence,
            )


class CompositeEventSink:
    def __init__(self, *sinks: EventSink) -> None:
        self.sinks = sinks

    def emit(self, event: ExecutionEvent) -> None:
        for sink in self.sinks:
            sink.emit(event)

    def events_for(self, run_id: str) -> list[ExecutionEvent]:
        if not self.sinks:
            return []
        return self.sinks[0].events_for(run_id)
