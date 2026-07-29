from __future__ import annotations

from collections import Counter
from threading import Lock

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


def configure_telemetry(service_name: str = "questpilot-api") -> None:
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        return
    trace.set_tracer_provider(
        TracerProvider(resource=Resource.create({"service.name": service_name}))
    )


def tracer():
    return trace.get_tracer("questpilot")


class AppMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[str] = Counter()
        self._latency_ms: Counter[str] = Counter()

    def observe(self, route: str, status_code: int, latency_ms: float) -> None:
        key = f"{route}|{status_code}"
        with self._lock:
            self._requests[key] += 1
            self._latency_ms[route] += int(latency_ms)

    def snapshot(self) -> dict:
        with self._lock:
            totals: Counter[str] = Counter()
            for key, count in self._requests.items():
                totals[key.split("|", 1)[0]] += count
            return {
                "requests": dict(self._requests),
                "average_latency_ms": {
                    route: round(self._latency_ms[route] / count, 2)
                    for route, count in totals.items()
                    if count
                },
            }
