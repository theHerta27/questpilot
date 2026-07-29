from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from time import monotonic
from typing import Any
from uuid import uuid4

from questpilot.harness.events import EventSink, ExecutionEvent, InMemoryEventSink


@dataclass
class ExecutionContext:
    user_id: str = "demo"
    locale: str = "zh-CN"
    model_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_sink: EventSink = field(default_factory=InMemoryEventSink)
    run_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    policy: Any | None = None
    _sequence: int = 0
    _started_monotonic: float = field(default_factory=monotonic)

    def emit(
        self,
        event_type: str,
        component: str,
        status: str,
        *,
        payload_summary: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
        finished: bool = False,
    ) -> ExecutionEvent:
        self._sequence += 1
        event = ExecutionEvent(
            run_id=self.run_id,
            sequence=self._sequence,
            event_type=event_type,
            component=component,
            status=status,
            payload_summary=payload_summary or {},
            error=error,
            usage=usage or {},
        )
        if finished:
            from datetime import datetime

            event.finished_at = datetime.now(UTC)
        self.event_sink.emit(event)
        return event

    @property
    def elapsed_seconds(self) -> float:
        return monotonic() - self._started_monotonic
