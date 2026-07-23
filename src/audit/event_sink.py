"""Fan-out sink for audit events to external systems (SIEM, webhooks, Kafka)."""
from typing import Dict, Any, List, Protocol
import logging
import json

logger = logging.getLogger(__name__)


class EventSink(Protocol):
    async def emit(self, event: Dict[str, Any]) -> None:
        ...


class LoggingSink:
    """Default sink: writes audit events to the application logger."""

    async def emit(self, event: Dict[str, Any]) -> None:
        logger.info(f"AUDIT_EVENT: {json.dumps(event, default=str)}")


class WebhookSink:
    """Forwards audit events to an external webhook (e.g. SIEM ingestion endpoint)."""

    def __init__(self, url: str):
        self.url = url

    async def emit(self, event: Dict[str, Any]) -> None:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self.url, json=event)
        except Exception as e:
            logger.error(f"Failed to emit audit event to webhook: {e}")


class EventSinkManager:
    """Holds a list of sinks and fans out each audit event to all of them."""

    def __init__(self):
        self.sinks: List[EventSink] = [LoggingSink()]

    def register(self, sink: EventSink):
        self.sinks.append(sink)

    async def emit_all(self, event: Dict[str, Any]):
        for sink in self.sinks:
            await sink.emit(event)
