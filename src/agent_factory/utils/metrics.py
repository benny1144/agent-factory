from __future__ import annotations

from prometheus_client import Summary, Counter

# Prometheus metrics definitions
request_latency = Summary("api_request_latency_seconds", "Latency of API requests")
# Use base name without _total; Prometheus client appends _total for counters in exposition
governance_events = Counter("governance_events", "Number of governance events logged")


def record_event() -> None:
    """Increment governance events counter."""
    governance_events.inc()

__all__ = [
    "request_latency",
    "governance_events",
    "record_event",
]
