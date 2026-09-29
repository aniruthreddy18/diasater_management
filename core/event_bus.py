"""
Asynchronous In-Memory Event Bus
Multi-Disaster Early Warning System
"""

import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """
    Decoupled publish-subscribe event bus.
    Facilitates event flow across receiver, classifier, engines, state, and alerts.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], Any]]] = {}

    def subscribe(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Subscribe a callable handler to a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug("Subscribed %s to topic '%s'", handler.__name__, topic)

    async def publish(self, topic: str, event: Any) -> None:
        """Publish an event to all subscribers of a topic."""
        handlers = self._subscribers.get(topic, [])
        if not handlers:
            return

        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    handler(event)
            except Exception as e:
                logger.error("Error executing sync handler %s on topic %s: %s", handler, topic, e)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("Error in async handler on topic %s: %s", topic, res)


# Global event bus singleton
event_bus = EventBus()
